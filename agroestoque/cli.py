"""Comandos de linha de comando:  flask --app agroestoque <comando>

    init-db           cria as tabelas (se ainda não existirem)
    criar-usuario     cria um usuário
    seed-demo         carrega dados demonstrativos
    importar-base     importa a base tratada da TED 02
"""
import csv
import math
import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import click

from . import servicos, util
from .analise import reconstruir_livro
from .auth import ADMINISTRADOR, GESTOR, OPERADOR, PAPEIS
from .config import RAIZ
from .db import get_db, init_db, transacao, triggers_suspensos
from .erros import ApiError
from .validacao import validar_senha

SENHA_PADRAO = "Agro@2026"
DIAS_HISTORICO = 60

USUARIOS_DEMO = [
    ("Administrador", "admin@daroca.com.br", ADMINISTRADOR),
    ("Gestor da Loja", "gestor@daroca.com.br", GESTOR),
    ("Operador de Estoque", "operador@daroca.com.br", OPERADOR),
]
FORNECEDORES_DEMO = [
    ("Nutrimais Distribuidora", "(99) 3541-0001", "vendas@nutrimais.example", 5),
    ("AgroSul Insumos", "(99) 3541-0002", "contato@agrosul.example", 7),
    ("PetBrasil Atacado", "(99) 3541-0003", "pedidos@petbrasil.example", 10),
]
# nome, sku, categoria, preço (centavos), saldo final, mínimo, média diária de vendas, fornecedor(idx)
PRODUTOS_DEMO = [
    ("Ração Canina Premium 15 kg", "RAC-001", "Rações", 18990, 4, 8, 1.1, 0),
    ("Milho Triturado 5 kg", "AGR-001", "Agropecuária", 3250, 12, 10, 1.4, 1),
    ("Areia Higiênica 4 kg", "PET-001", "Pet", 2490, 28, 8, 1.0, 2),
    ("Suplemento Mineral 20 kg", "NUT-001", "Nutrição animal", 14800, 2, 5, 0.4, 0),
    ("Coleira Antipulgas", "PET-002", "Pet", 4890, 17, 6, 0.5, 2),
    ("Semente de Capim 2 kg", "AGR-002", "Agropecuária", 7600, 9, 8, 0.6, 1),
    ("Ração Felina 10 kg", "RAC-002", "Rações", 12990, 31, 10, 0.9, 0),
    ("Sal Mineralizado 25 kg", "NUT-002", "Nutrição animal", 9600, 40, 12, 1.2, 0),
    ("Vermífugo Bovino 50 ml", "VET-001", "Veterinária", 5490, 22, 10, 0.7, 1),
    ("Shampoo Pet Neutro 500 ml", "PET-003", "Pet", 2790, 36, 8, 0.8, 2),
    ("Arame Farpado 500 m", "AGR-003", "Agropecuária", 38900, 7, 4, 0.2, 1),
    ("Ração para Aves 25 kg", "RAC-003", "Rações", 8800, 15, 12, 1.6, 1),
]
CATEGORIAS_PT = {"Groceries": "Mercearia", "Toys": "Brinquedos", "Electronics": "Eletrônicos",
                 "Furniture": "Móveis", "Clothing": "Vestuário"}
CSV_PADRAO = RAIZ / "data" / "processed" / "retail_store_inventory_processed.csv"


def _inserir_livro(db, produto_id, linhas, saldo_final, hora_entrada, hora_saida, preco_centavos,
                   deslocamento, observacao, hora_inicial=6, rng=None, custo_centavos=None):
    """Grava o livro de movimentações reconstruído (saldo coerente até o saldo final)."""
    inicial, efetivas, ajustes = reconstruir_livro(linhas, saldo_final)
    registros, saldo = [], 0

    def novo(d, hora, tipo, motivo, qtd, valor, obs):
        nonlocal saldo
        saldo += qtd if tipo == "ENTRADA" else -qtd
        minuto = rng.randint(0, 59) if rng else 0
        registros.append((produto_id, tipo, motivo, qtd, valor, saldo, obs,
                          util.local_para_db(d + deslocamento, hora, minuto)))

    if inicial > 0:
        novo(linhas[0][0], hora_inicial, "ENTRADA", "ESTOQUE_INICIAL", inicial, None, observacao)
    for d, ent, sai in efetivas:
        if ent > 0:
            novo(d, hora_entrada, "ENTRADA", "COMPRA", ent, custo_centavos, observacao)
        if sai > 0:
            hora = rng.randint(9, 18) if rng else hora_saida
            novo(d, hora, "SAIDA", "VENDA", sai, preco_centavos, observacao)
    db.executemany(
        """INSERT INTO movimentacao (produto_id, tipo, motivo, quantidade, valor_unitario_centavos,
           saldo_apos, observacao, data) VALUES (?,?,?,?,?,?,?,?)""", registros)
    return len(registros), ajustes


def registrar(app):
    @app.cli.command("init-db")
    def cmd_init_db():
        """Cria as tabelas do banco de dados (se ainda não existirem)."""
        init_db(get_db())
        click.echo(f"Banco pronto em {app.config['DATABASE']}")

    @app.cli.command("criar-usuario")
    @click.option("--nome", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--papel", type=click.Choice(PAPEIS), default=OPERADOR, show_default=True)
    @click.option("--senha", prompt=True, hide_input=True, confirmation_prompt=True)
    def cmd_criar_usuario(nome, email, papel, senha):
        """Cria um usuário (use para o primeiro administrador em produção)."""
        try:
            validar_senha(senha)
            servicos.criar_usuario(get_db(), nome.strip(), email.strip().lower(), senha, papel)
        except ApiError as e:
            raise click.ClickException(e.mensagem + " " + str(e.detalhes))
        click.echo(f"Usuário {email} criado com o perfil {papel}.")

    @app.cli.command("seed-demo")
    @click.option("--senha", default=SENHA_PADRAO, show_default=True, help="Senha dos usuários de demonstração.")
    @click.option("--limpar", is_flag=True, help="Apaga produtos, movimentações e recomendações antes.")
    def cmd_seed_demo(senha, limpar):
        """Carrega usuários, fornecedores, produtos e 60 dias de vendas de demonstração."""
        db = get_db()
        with transacao(db):
            if limpar:
                with triggers_suspensos(db):
                    db.execute("DELETE FROM recomendacao")
                    db.execute("DELETE FROM movimentacao")
                    db.execute("DELETE FROM produto")
            skus = [p[1] for p in PRODUTOS_DEMO]
            if db.execute(f"SELECT 1 FROM produto WHERE sku IN ({','.join('?' * len(skus))})", skus).fetchone():
                click.echo("Produtos de demonstração já existem. Use --limpar para recarregar.")
                return
            for nome, email, papel in USUARIOS_DEMO:
                existente = db.execute("SELECT id FROM usuario WHERE email = ?", (email,)).fetchone()
                if existente:
                    db.execute("UPDATE usuario SET papel = ?, ativo = 1 WHERE id = ?", (papel, existente["id"]))
                else:
                    servicos.criar_usuario(db, nome, email, senha, papel)
            ids_forn = []
            for nome, tel, email, prazo in FORNECEDORES_DEMO:
                linha = db.execute("SELECT id FROM fornecedor WHERE nome = ?", (nome,)).fetchone()
                ids_forn.append(linha["id"] if linha else db.execute(
                    "INSERT INTO fornecedor (nome, telefone, email, prazo_entrega_dias) VALUES (?,?,?,?)",
                    (nome, tel, email, prazo)).lastrowid)

            rng = random.Random(2026)
            hoje = util.hoje_local()
            dias = [hoje - timedelta(days=DIAS_HISTORICO - 1 - i) for i in range(DIAS_HISTORICO)]
            total = 0
            for nome, sku, cat, preco, saldo_final, minimo, media, forn in PRODUTOS_DEMO:
                cat_id, _ = servicos.obter_ou_criar_categoria(db, cat)
                pid = db.execute(
                    """INSERT INTO produto (sku, nome, categoria_id, preco_venda_centavos, quantidade_atual,
                       estoque_minimo, fornecedor_id) VALUES (?,?,?,?,?,?,?)""",
                    (sku, nome, cat_id, preco, saldo_final, minimo, ids_forn[forn])).lastrowid
                saidas = []
                for i, d in enumerate(dias):
                    fator = 1.25 if d.weekday() >= 5 else 1.0
                    if i >= DIAS_HISTORICO - 21:  # últimas três semanas: leve aceleração
                        fator *= 1.18
                    saidas.append(max(0, round(rng.gauss(media * fator, max(0.5, media * 0.6)))))
                entradas = [0] * DIAS_HISTORICO
                for i in rng.sample(range(5, DIAS_HISTORICO - 5), 2):  # duas compras no período
                    entradas[i] = max(1, round(media * 12))
                n, _ = _inserir_livro(db, pid, list(zip(dias, entradas, saidas)), saldo_final, 8, 12,
                                      preco, timedelta(0), "Carga de demonstração", rng=rng,
                                      custo_centavos=int(preco * 0.7))
                total += n
            _, pendentes = servicos.gerar_recomendacoes(db)
        click.echo(f"Demonstração carregada: {len(PRODUTOS_DEMO)} produtos, {total} movimentações, "
                   f"{pendentes} recomendações pendentes.")
        click.echo(f"Usuários (senha: {senha}):")
        for _, email, papel in USUARIOS_DEMO:
            click.echo(f"  - {email}  [{papel}]")

    @app.cli.command("importar-base")
    @click.option("--csv", "caminho", default=str(CSV_PADRAO), show_default=True)
    @click.option("--dias", default=90, show_default=True, help="Quantidade de dias finais a importar.")
    @click.option("--loja", default=None, help="Filtra uma loja (ex.: S001).")
    @click.option("--sem-deslocamento", is_flag=True, help="Mantém as datas originais.")
    @click.option("--limpar", is_flag=True, help="Reimporta produtos já existentes (apaga o histórico deles).")
    def cmd_importar(caminho, dias, loja, sem_deslocamento, limpar):
        """Importa a base tratada da TED 02 (73 mil registros) para o banco."""
        if not Path(caminho).exists():
            raise click.ClickException(f"Arquivo não encontrado: {caminho}")
        base = {}
        with open(caminho, newline="", encoding="utf-8") as f:
            for l in csv.DictReader(f):
                if loja and l["Store ID"] != loja:
                    continue
                p = base.setdefault(l["Product ID"], {"cat": l["Category"], "precos": [],
                                                     "dias": defaultdict(lambda: [0, 0, 0])})
                reg = p["dias"][date.fromisoformat(l["Date"])]
                reg[0] += int(float(l["Units Ordered"]))
                reg[1] += int(float(l["Units Sold"]))
                reg[2] += int(float(l["Inventory Level"]))
                p["precos"].append(Decimal(l["Price"]))
        if not base:
            raise click.ClickException("Nenhum registro encontrado na base informada.")

        ultima = max(max(p["dias"]) for p in base.values())
        desloc = timedelta(0) if sem_deslocamento else (util.hoje_local() - ultima)
        db = get_db()
        criados = total = 0
        with transacao(db):
            for pid_csv, info in sorted(base.items()):
                datas = sorted(info["dias"])[-dias:]
                existente = db.execute("SELECT id FROM produto WHERE sku = ?", (pid_csv,)).fetchone()
                if existente and not limpar:
                    click.echo(f"  {pid_csv}: já existe (use --limpar para reimportar)")
                    continue
                if existente:
                    with triggers_suspensos(db):
                        db.execute("DELETE FROM recomendacao WHERE produto_id = ?", (existente["id"],))
                        db.execute("DELETE FROM movimentacao WHERE produto_id = ?", (existente["id"],))
                        db.execute("DELETE FROM produto WHERE id = ?", (existente["id"],))
                cat = CATEGORIAS_PT.get(info["cat"], info["cat"])
                cat_id, _ = servicos.obter_ou_criar_categoria(db, cat)
                preco = int((sum(info["precos"]) / len(info["precos"]) * 100).to_integral_value())
                media = sum(info["dias"][d][1] for d in datas) / len(datas)
                saldo_final = info["dias"][datas[-1]][2]
                pid = db.execute(
                    """INSERT INTO produto (sku, nome, categoria_id, preco_venda_centavos, quantidade_atual,
                       estoque_minimo) VALUES (?,?,?,?,?,?)""",
                    (pid_csv, f"{cat} {pid_csv}", cat_id, preco, saldo_final, math.ceil(media))).lastrowid
                linhas = [(d, info["dias"][d][0], info["dias"][d][1]) for d in datas]
                n, aj = _inserir_livro(db, pid, linhas, saldo_final, 8, 12, preco, desloc,
                                       "Importado da base TED 02")
                criados += 1
                total += n
                click.echo(f"  {pid_csv}: {n} movimentações ({aj} entradas ajustadas)")
            _, pendentes = servicos.gerar_recomendacoes(db)
        click.echo(f"Importação concluída: {criados} produtos, {total} movimentações, {pendentes} recomendações pendentes.")
