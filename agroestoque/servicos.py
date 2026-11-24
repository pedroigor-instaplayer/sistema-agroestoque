"""Regras de negócio do AgroEstoque (camada entre a API e o banco)."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from . import analise, util
from .auth import PAPEIS, hash_senha
from .db import sem_acento, transacao
from .erros import ApiError, erro_campo, nao_encontrado, regra

HORAS_SILENCIO_DECISAO = 24

MOTIVOS_POR_TIPO = {
    "ENTRADA": ("COMPRA", "DEVOLUCAO_CLIENTE", "AJUSTE_POSITIVO", "ESTOQUE_INICIAL"),
    "SAIDA": ("VENDA", "PERDA", "AJUSTE_NEGATIVO", "DEVOLUCAO_FORNECEDOR"),
}
DESCRICAO_MOTIVO = {
    "COMPRA": "Compra de fornecedor", "DEVOLUCAO_CLIENTE": "Devolução de cliente",
    "AJUSTE_POSITIVO": "Ajuste de inventário (+)", "ESTOQUE_INICIAL": "Estoque inicial",
    "VENDA": "Venda", "PERDA": "Perda ou avaria", "AJUSTE_NEGATIVO": "Ajuste de inventário (-)",
    "DEVOLUCAO_FORNECEDOR": "Devolução a fornecedor",
}

SQL_FROM_PRODUTO = """FROM produto p
    JOIN categoria c ON c.id = p.categoria_id
    LEFT JOIN fornecedor f ON f.id = p.fornecedor_id"""
SQL_COLUNAS_PRODUTO = ("SELECT p.*, c.nome AS categoria, f.nome AS fornecedor, "
                       "f.prazo_entrega_dias AS prazo_entrega_dias")
SQL_PRODUTO = f"{SQL_COLUNAS_PRODUTO} {SQL_FROM_PRODUTO}"

# situação por saldo (mesma regra de analise.situacao_por_saldo, aplicada no banco)
SQL_CRITICO = "(p.quantidade_atual <= 0 OR (p.estoque_minimo > 0 AND p.quantidade_atual <= p.estoque_minimo))"
SQL_ATENCAO = f"(NOT {SQL_CRITICO} AND p.estoque_minimo > 0 AND p.quantidade_atual * 2 <= p.estoque_minimo * 3)"
SQL_NORMAL = f"(NOT {SQL_CRITICO} AND NOT {SQL_ATENCAO})"
FILTROS_SITUACAO = {analise.CRITICO: SQL_CRITICO, analise.ATENCAO: SQL_ATENCAO, analise.NORMAL: SQL_NORMAL}


def like(termo):
    """Padrão LIKE sem acento/caixa, com escape de curingas."""
    t = sem_acento(termo).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{t}%"


# ------------------------------------------------------------- usuários
def criar_usuario(db, nome, email, senha, papel):
    if papel not in PAPEIS:
        raise erro_campo("papel", f"Use um destes valores: {', '.join(PAPEIS)}.")
    if db.execute("SELECT 1 FROM usuario WHERE email = ?", (email,)).fetchone():
        raise erro_campo("email", "Já existe um usuário com este e-mail.")
    cur = db.execute(
        "INSERT INTO usuario (nome, email, senha_hash, papel) VALUES (?,?,?,?)",
        (nome, email, hash_senha(senha), papel))
    return cur.lastrowid


def buscar_usuario(db, uid):
    u = db.execute("SELECT * FROM usuario WHERE id = ?", (uid,)).fetchone()
    if u is None:
        raise nao_encontrado("Usuário não encontrado.")
    return u


# ------------------------------------------------------- categorias/produtos
def obter_ou_criar_categoria(db, nome):
    linha = db.execute("SELECT id FROM categoria WHERE nome = ?", (nome,)).fetchone()
    if linha:
        return linha["id"], False
    return db.execute("INSERT INTO categoria (nome) VALUES (?)", (nome,)).lastrowid, True


def buscar_produto(db, pid):
    p = db.execute(SQL_PRODUTO + " WHERE p.id = ?", (pid,)).fetchone()
    if p is None:
        raise nao_encontrado("Produto não encontrado.")
    return p


def _gerar_sku(db):
    n = (db.execute("SELECT COALESCE(MAX(id), 0) FROM produto").fetchone()[0]) + 1
    while db.execute("SELECT 1 FROM produto WHERE sku = ?", (f"PRD{n:05d}",)).fetchone():
        n += 1
    return f"PRD{n:05d}"


def _checar_fornecedor(db, fid):
    if fid is not None and not db.execute("SELECT 1 FROM fornecedor WHERE id = ?", (fid,)).fetchone():
        raise erro_campo("fornecedor_id", "Fornecedor inexistente.")


def criar_produto(db, d, usuario_id=None, agora=None):
    """Cria o produto e, havendo quantidade inicial, a movimentação ESTOQUE_INICIAL."""
    with transacao(db):
        _checar_fornecedor(db, d.get("fornecedor_id"))
        sku = d.get("sku") or _gerar_sku(db)
        if db.execute("SELECT 1 FROM produto WHERE sku = ?", (sku,)).fetchone():
            raise erro_campo("sku", "Já existe um produto com este código.")
        cat_id, _ = obter_ou_criar_categoria(db, d["categoria"])
        agora_db = util.para_db(agora or util.agora_utc())
        pid = db.execute(
            """INSERT INTO produto (sku, nome, categoria_id, unidade, preco_venda_centavos,
                                    quantidade_atual, estoque_minimo, fornecedor_id, criado_em, atualizado_em)
               VALUES (?,?,?,?,?,0,?,?,?,?)""",
            (sku, d["nome"], cat_id, d["unidade"], d["preco_centavos"], d["estoque_minimo"],
             d.get("fornecedor_id"), agora_db, agora_db)).lastrowid
        if d.get("quantidade_inicial", 0) > 0:
            registrar_movimentacao(db, pid, "ENTRADA", "ESTOQUE_INICIAL", d["quantidade_inicial"],
                                   usuario_id=usuario_id, observacao="Cadastro do produto", agora=agora)
        return pid


def atualizar_produto(db, pid, campos, agora=None):
    """Atualiza campos do produto. O saldo NUNCA é alterado aqui."""
    with transacao(db):
        buscar_produto(db, pid)
        if "sku" in campos and db.execute(
                "SELECT 1 FROM produto WHERE sku = ? AND id <> ?", (campos["sku"], pid)).fetchone():
            raise erro_campo("sku", "Já existe um produto com este código.")
        if "fornecedor_id" in campos:
            _checar_fornecedor(db, campos["fornecedor_id"])
        sets, params = [], []
        if "categoria" in campos:
            cat_id, _ = obter_ou_criar_categoria(db, campos.pop("categoria"))
            campos["categoria_id"] = cat_id
        for coluna in ("nome", "sku", "categoria_id", "unidade", "preco_venda_centavos",
                       "estoque_minimo", "fornecedor_id", "ativo"):
            if coluna in campos:
                sets.append(f"{coluna} = ?")
                params.append(campos[coluna])
        sets.append("atualizado_em = ?")
        params.append(util.para_db(agora or util.agora_utc()))
        db.execute(f"UPDATE produto SET {', '.join(sets)} WHERE id = ?", (*params, pid))
        produto = buscar_produto(db, pid)
        if produto["ativo"]:
            avaliar_produto(db, produto, agora=agora)
        else:
            _expirar_pendentes(db, pid)
        return produto


def _expirar_pendentes(db, pid):
    db.execute("UPDATE recomendacao SET status = 'EXPIRADA' WHERE produto_id = ? AND status = 'PENDENTE'", (pid,))


def desativar_produto(db, pid, agora=None):
    return atualizar_produto(db, pid, {"ativo": 0}, agora=agora)


# ------------------------------------------------------------ movimentações
def registrar_movimentacao(db, produto_id, tipo, motivo, quantidade, usuario_id=None,
                           observacao="", valor_unitario_centavos=None, agora=None):
    """Registra a movimentação e atualiza o saldo de forma atômica.

    Regras: produto ativo; quantidade >= 1; motivo compatível com o tipo;
    saída não pode exceder o saldo disponível.
    """
    with transacao(db):
        produto = db.execute("SELECT * FROM produto WHERE id = ?", (produto_id,)).fetchone()
        if produto is None:
            raise regra("PRODUTO_NAO_ENCONTRADO", "Produto não encontrado.")
        if not produto["ativo"]:
            raise regra("PRODUTO_INATIVO", "Produto inativo não pode ser movimentado.")
        if quantidade < 1:
            raise regra("QUANTIDADE_INVALIDA", "A quantidade deve ser maior que zero.")
        if motivo not in MOTIVOS_POR_TIPO.get(tipo, ()):
            raise regra("MOTIVO_INCOMPATIVEL",
                        f"O motivo '{motivo}' não é válido para movimentações do tipo '{tipo}'.",
                        {"motivos_validos": list(MOTIVOS_POR_TIPO.get(tipo, ()))})
        saldo = produto["quantidade_atual"]
        if tipo == "SAIDA":
            if quantidade > saldo:
                raise regra("ESTOQUE_INSUFICIENTE",
                            f"Estoque insuficiente: saldo atual de {saldo} e saída solicitada de {quantidade}.",
                            {"saldo_atual": saldo, "solicitado": quantidade})
            novo_saldo = saldo - quantidade
        else:
            novo_saldo = saldo + quantidade
        if valor_unitario_centavos is None and motivo == "VENDA":
            valor_unitario_centavos = produto["preco_venda_centavos"]  # preço no momento da venda

        agora = agora or util.agora_utc()
        mov_id = db.execute(
            """INSERT INTO movimentacao (produto_id, tipo, motivo, quantidade, valor_unitario_centavos,
                                         saldo_apos, observacao, usuario_id, data)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (produto_id, tipo, motivo, quantidade, valor_unitario_centavos, novo_saldo,
             observacao or "", usuario_id, util.para_db(agora))).lastrowid
        db.execute("UPDATE produto SET quantidade_atual = ?, atualizado_em = ? WHERE id = ?",
                   (novo_saldo, util.para_db(agora), produto_id))
        avaliar_produto(db, buscar_produto(db, produto_id), agora=agora)  # alertas sempre atualizados
        return mov_id


def buscar_movimentacao(db, mid):
    return db.execute(
        """SELECT m.*, p.nome AS produto, u.email AS usuario FROM movimentacao m
           JOIN produto p ON p.id = m.produto_id LEFT JOIN usuario u ON u.id = m.usuario_id
           WHERE m.id = ?""", (mid,)).fetchone()


# ------------------------------------------- séries, análise e recomendação
def series_por_produto(db, produto_ids=None, dias=analise.JANELA_DIAS, agora=None):
    """Vendas diárias (motivo VENDA) por produto: ({id: [qtd...]}, [datas]) do mais antigo ao mais recente."""
    hoje = util.hoje_local(agora)
    inicio = hoje - timedelta(days=dias - 1)
    sql = ("SELECT produto_id, data, quantidade FROM movimentacao "
           "WHERE tipo = 'SAIDA' AND motivo = 'VENDA' AND data >= ? AND data < ?")
    params = [util.inicio_dia_db(inicio), util.inicio_dia_db(hoje + timedelta(days=1))]
    if produto_ids is not None:
        ids = list(produto_ids)
        if not ids:
            return {}, []
        sql += f" AND produto_id IN ({','.join('?' * len(ids))})"
        params += ids
    por_produto = defaultdict(lambda: defaultdict(int))
    for linha in db.execute(sql, params):
        por_produto[linha["produto_id"]][util.data_local(linha["data"])] += linha["quantidade"]
    datas = [inicio + timedelta(days=i) for i in range(dias)]
    ids = list(produto_ids) if produto_ids is not None else list(por_produto.keys())
    return {pid: [por_produto[pid].get(d, 0) for d in datas] for pid in ids}, datas


def analisar_produto(produto, serie):
    return analise.analisar(produto["quantidade_atual"], produto["estoque_minimo"], serie,
                            prazo_entrega_dias=produto["prazo_entrega_dias"])


def avaliar_produto(db, produto, serie=None, agora=None):
    """Cria, atualiza ou expira a recomendação pendente do produto."""
    agora = agora or util.agora_utc()
    if serie is None:
        series, _ = series_por_produto(db, [produto["id"]], agora=agora)
        serie = series[produto["id"]]
    res = analisar_produto(produto, serie)
    pendente = db.execute(
        "SELECT id FROM recomendacao WHERE produto_id = ? AND status = 'PENDENTE'",
        (produto["id"],)).fetchone()

    if res.nivel == analise.NORMAL:
        if pendente:
            db.execute("UPDATE recomendacao SET status = 'EXPIRADA' WHERE id = ?", (pendente["id"],))
        return None

    campos = (res.nivel, res.quantidade_sugerida, res.saldo, res.demanda_diaria,
              res.dias_cobertura, res.tendencia_pct, res.acao_sugerida, res.justificativa,
              util.para_db(agora))
    if pendente:
        db.execute(
            """UPDATE recomendacao SET nivel=?, quantidade_sugerida=?, saldo_no_calculo=?, media_diaria=?,
               dias_cobertura=?, tendencia_percentual=?, acao_sugerida=?, justificativa=?, gerada_em=?
               WHERE id = ?""", (*campos, pendente["id"]))
        return pendente["id"]

    limite = util.para_db(agora - timedelta(hours=HORAS_SILENCIO_DECISAO))
    if db.execute(
            "SELECT 1 FROM recomendacao WHERE produto_id = ? AND status IN ('ACEITA','IGNORADA') "
            "AND decidida_em >= ?", (produto["id"], limite)).fetchone():
        return None  # o gestor acabou de decidir; não insistir
    return db.execute(
        """INSERT INTO recomendacao (produto_id, nivel, quantidade_sugerida, saldo_no_calculo, media_diaria,
           dias_cobertura, tendencia_percentual, acao_sugerida, justificativa, gerada_em)
           VALUES (?,?,?,?,?,?,?,?,?,?)""", (produto["id"], *campos)).lastrowid


def gerar_recomendacoes(db, agora=None):
    """Reavalia todos os produtos ativos. Retorna (criadas_ou_atualizadas, total_pendentes)."""
    produtos = db.execute(SQL_PRODUTO + " WHERE p.ativo = 1").fetchall()
    series, _ = series_por_produto(db, None, agora=agora)
    afetadas = 0
    with transacao(db):
        for p in produtos:
            serie = series.get(p["id"]) or [0] * analise.JANELA_DIAS
            if avaliar_produto(db, p, serie, agora=agora):
                afetadas += 1
    pendentes = db.execute("SELECT COUNT(*) FROM recomendacao WHERE status = 'PENDENTE'").fetchone()[0]
    return afetadas, pendentes


def decidir_recomendacao(db, rid, status, usuario_id):
    if status not in ("ACEITA", "IGNORADA"):
        raise regra("STATUS_INVALIDO", "O status deve ser ACEITA ou IGNORADA.")
    with transacao(db):
        rec = db.execute("SELECT * FROM recomendacao WHERE id = ?", (rid,)).fetchone()
        if rec is None:
            raise regra("RECOMENDACAO_NAO_ENCONTRADA", "Recomendação não encontrada.")
        if rec["status"] != "PENDENTE":
            raise regra("RECOMENDACAO_JA_DECIDIDA", f"A recomendação já está com status {rec['status']}.")
        db.execute("UPDATE recomendacao SET status=?, decidida_em=?, decidida_por_id=? WHERE id=?",
                   (status, util.para_db(util.agora_utc()), usuario_id, rid))
    return buscar_recomendacao(db, rid)


def buscar_recomendacao(db, rid):
    return db.execute(
        """SELECT r.*, p.nome AS produto, p.sku AS sku, p.quantidade_atual AS saldo_atual,
                  u.email AS decidida_por
           FROM recomendacao r JOIN produto p ON p.id = r.produto_id
           LEFT JOIN usuario u ON u.id = r.decidida_por_id WHERE r.id = ?""", (rid,)).fetchone()


# ---------------------------------------------------------------- dashboard
_DIAS_SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


def _soma_vendas(db, inicio, fim):
    """Retorna unidades vendidas e faturamento em centavos."""
    linha = db.execute(
        """
        SELECT
            COALESCE(SUM(quantidade), 0) AS unidades,
            COALESCE(
                SUM(quantidade * valor_unitario_centavos), 0
            ) AS centavos
        FROM movimentacao
        WHERE tipo = 'SAIDA'
          AND motivo = 'VENDA'
          AND data >= ?
          AND data < ?
        """,
        (
            util.inicio_dia_db(inicio),
            util.inicio_dia_db(fim),
        ),
    ).fetchone()

    return linha["unidades"], linha["centavos"]


def montar_dashboard(db, agora=None):
    hoje = util.hoje_local(agora)
    amanha = hoje + timedelta(days=1)
    contar = lambda filtro: db.execute(
        f"SELECT COUNT(*) FROM produto p WHERE p.ativo = 1 AND {filtro}").fetchone()[0]
    criticos, atencao = contar(SQL_CRITICO), contar(SQL_ATENCAO)

    inicio_mes = hoje.replace(day=1)
    fim_mes_ant = inicio_mes - timedelta(days=1)
    inicio_mes_ant = fim_mes_ant.replace(day=1)
    corte_ant = min(inicio_mes_ant + timedelta(days=(hoje - inicio_mes).days), fim_mes_ant)
    qtd_mes, centavos_mes = _soma_vendas(db, inicio_mes, amanha)
    qtd_ant, _ = _soma_vendas(db, inicio_mes_ant, corte_ant + timedelta(days=1))
    variacao = round((qtd_mes - qtd_ant) / qtd_ant * 100, 1) if qtd_ant else None

    inicio7 = hoje - timedelta(days=6)
    por_dia = defaultdict(int)
    for l in db.execute(
            """SELECT data, quantidade FROM movimentacao WHERE tipo='SAIDA' AND motivo='VENDA'
               AND data >= ? AND data < ?""", (util.inicio_dia_db(inicio7), util.inicio_dia_db(amanha))):
        por_dia[util.data_local(l["data"])] += l["quantidade"]
    saidas7 = []
    for i in range(7):
        d = inicio7 + timedelta(days=i)
        saidas7.append({"data": d.isoformat(), "rotulo": _DIAS_SEMANA[d.weekday()], "quantidade": por_dia.get(d, 0)})

    mais_vendidos = [
        {"produto_id": l["produto_id"], "produto": l["nome"], "quantidade": l["total"]}
        for l in db.execute(
            """SELECT m.produto_id, p.nome, SUM(m.quantidade) AS total FROM movimentacao m
               JOIN produto p ON p.id = m.produto_id
               WHERE m.tipo='SAIDA' AND m.motivo='VENDA' AND m.data >= ? AND m.data < ?
               GROUP BY m.produto_id, p.nome ORDER BY total DESC, p.nome LIMIT 5""",
            (util.inicio_dia_db(hoje - timedelta(days=29)), util.inicio_dia_db(amanha)))]

    exigem = [
        {"recomendacao_id": l["id"], "produto_id": l["produto_id"], "produto": l["nome"],
         "nivel": l["nivel"], "saldo": l["quantidade_atual"]}
        for l in db.execute(
            """SELECT r.id, r.produto_id, r.nivel, p.nome, p.quantidade_atual FROM recomendacao r
               JOIN produto p ON p.id = r.produto_id WHERE r.status = 'PENDENTE'
               ORDER BY CASE r.nivel WHEN 'CRITICO' THEN 0 ELSE 1 END,
                        (r.dias_cobertura IS NULL), r.dias_cobertura, r.gerada_em DESC LIMIT 5""")]

    return {
        "data_referencia": hoje.isoformat(),
        "total_produtos": db.execute("SELECT COUNT(*) FROM produto WHERE ativo = 1").fetchone()[0],
        "total_categorias": db.execute(
            "SELECT COUNT(DISTINCT categoria_id) FROM produto WHERE ativo = 1").fetchone()[0],
        "estoque_baixo": criticos + atencao,
        "itens_criticos": criticos,
        "vendas_mes_unidades": qtd_mes,
        "variacao_vendas_percentual": variacao,
        "faturamento_mes": util.centavos_str(centavos_mes),
        "recomendacoes_pendentes": db.execute(
            "SELECT COUNT(*) FROM recomendacao WHERE status = 'PENDENTE'").fetchone()[0],
        "saidas_ultimos_7_dias": saidas7,
        "produtos_mais_vendidos": mais_vendidos,
        "produtos_exigem_acao": exigem,
    }
