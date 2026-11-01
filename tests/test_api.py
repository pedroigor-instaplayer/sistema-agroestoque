"""Testes de integração da API (executar com:  python -m unittest discover -s tests -v)."""
import os
import sqlite3
import tempfile
import unittest
from datetime import timedelta

from agroestoque import create_app, servicos, util
from agroestoque.db import get_db, triggers_suspensos

SENHA = "Senha@12345"


class ApiBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "DATABASE": os.path.join(self.tmp.name, "t.sqlite3"),
                               "SECRET_KEY": "chave-de-teste", "PASSWORD_ITERACOES": 1000})
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.db = get_db()
        for nome, papel in (("Gestor", "GESTOR"), ("Operador", "OPERADOR"), ("Admin", "ADMINISTRADOR")):
            servicos.criar_usuario(self.db, nome, f"{papel.lower()}@teste.com", SENHA, papel)
        self.cat_id, _ = servicos.obter_ou_criar_categoria(self.db, "Rações")
        self._tokens = {}

    def tearDown(self):
        self.ctx.pop()
        self.tmp.cleanup()

    # ---- helpers
    def token(self, papel):
        if papel not in self._tokens:
            r = self.client.post("/api/auth/login", json={"email": f"{papel}@teste.com", "senha": SENHA})
            self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
            self._tokens[papel] = r.get_json()["token"]
        return self._tokens[papel]

    def chamar(self, metodo, url, dados=None, papel="gestor", token=None):
        headers = {}
        tk = token or (self.token(papel) if papel else None)
        if tk:
            headers["Authorization"] = "Bearer " + tk
        kwargs = {"headers": headers}
        if dados is not None:
            kwargs["json"] = dados
        return getattr(self.client, metodo)(url, **kwargs)

    def produto(self, saldo=20, minimo=5, sku="P1", preco_centavos=1000, ativo=1):
        cur = self.db.execute(
            """INSERT INTO produto (sku, nome, categoria_id, preco_venda_centavos, quantidade_atual,
               estoque_minimo, ativo) VALUES (?,?,?,?,?,?,?)""",
            (sku, "Produto " + sku, self.cat_id, preco_centavos, saldo, minimo, ativo))
        return cur.lastrowid

    def saldo(self, pid):
        return self.db.execute("SELECT quantidade_atual FROM produto WHERE id=?", (pid,)).fetchone()[0]


class AutenticacaoTests(ApiBase):
    def test_login_valido_retorna_token_e_papel(self):
        r = self.client.post("/api/auth/login", json={"email": "GESTOR@teste.com", "senha": SENHA})
        self.assertEqual(r.status_code, 200)
        corpo = r.get_json()
        self.assertTrue(corpo["token"])
        self.assertEqual(corpo["usuario"]["papel"], "GESTOR")
        self.assertNotIn("senha_hash", corpo["usuario"])

    def test_senha_nao_e_guardada_em_texto_puro(self):
        h = self.db.execute("SELECT senha_hash FROM usuario WHERE email='gestor@teste.com'").fetchone()[0]
        self.assertNotIn(SENHA, h)
        self.assertTrue(h.startswith("pbkdf2:sha256"))

    def test_login_senha_errada(self):
        r = self.client.post("/api/auth/login", json={"email": "gestor@teste.com", "senha": "errada"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json()["erro"]["codigo"], "CREDENCIAIS_INVALIDAS")

    def test_login_email_inexistente_tem_mesma_resposta(self):
        r = self.client.post("/api/auth/login", json={"email": "ninguem@teste.com", "senha": "x"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json()["erro"]["codigo"], "CREDENCIAIS_INVALIDAS")

    def test_login_sem_campos_e_json_invalido(self):
        self.assertEqual(self.client.post("/api/auth/login", json={}).status_code, 400)
        r = self.client.post("/api/auth/login", data="{isso nao e json", content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.get_json()["erro"]["codigo"], "JSON_INVALIDO")

    def test_bloqueio_apos_tentativas(self):
        for _ in range(5):
            self.client.post("/api/auth/login", json={"email": "gestor@teste.com", "senha": "x"})
        r = self.client.post("/api/auth/login", json={"email": "gestor@teste.com", "senha": SENHA})
        self.assertEqual(r.status_code, 429)

    def test_rota_protegida_exige_token(self):
        self.assertEqual(self.client.get("/api/produtos").status_code, 401)
        self.assertEqual(self.chamar("get", "/api/produtos", token="invalido", papel=None).status_code, 401)

    def test_token_expirado(self):
        tk = self.token("gestor")
        self.app.config["TOKEN_TTL_SEGUNDOS"] = -1
        r = self.chamar("get", "/api/auth/me", token=tk, papel=None)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.get_json()["erro"]["codigo"], "TOKEN_EXPIRADO")

    def test_usuario_inativo_nao_acessa(self):
        tk = self.token("operador")
        self.db.execute("UPDATE usuario SET ativo = 0 WHERE email='operador@teste.com'")
        self.assertEqual(self.chamar("get", "/api/auth/me", token=tk, papel=None).status_code, 401)
        r = self.client.post("/api/auth/login", json={"email": "operador@teste.com", "senha": SENHA})
        self.assertEqual(r.status_code, 401)

    def test_troca_de_senha_invalida_token_antigo(self):
        tk = self.token("operador")
        r = self.chamar("post", "/api/auth/alterar-senha",
                        {"senha_atual": SENHA, "nova_senha": "NovaSenha#2026"}, papel="operador")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.chamar("get", "/api/auth/me", token=tk, papel=None).status_code, 401)
        r = self.client.post("/api/auth/login", json={"email": "operador@teste.com", "senha": "NovaSenha#2026"})
        self.assertEqual(r.status_code, 200)

    def test_alterar_senha_valida_politica(self):
        r = self.chamar("post", "/api/auth/alterar-senha", {"senha_atual": SENHA, "nova_senha": "12345678"})
        self.assertEqual(r.status_code, 400)
        r = self.chamar("post", "/api/auth/alterar-senha", {"senha_atual": "errada", "nova_senha": "OutraSenha#1"})
        self.assertEqual(r.status_code, 400)

    def test_saude_rota_inexistente_e_metodo(self):
        self.assertEqual(self.client.get("/api/saude").status_code, 200)
        r = self.client.get("/api/nao-existe")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["erro"]["codigo"], "ROTA_NAO_ENCONTRADA")
        r = self.chamar("delete", "/api/dashboard")
        self.assertEqual(r.status_code, 405)
        self.assertEqual(r.get_json()["erro"]["codigo"], "METODO_NAO_PERMITIDO")

    def test_cabecalhos_de_seguranca(self):
        r = self.client.get("/api/saude")
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(r.headers["Cache-Control"], "no-store")


class UsuarioTests(ApiBase):
    def test_apenas_admin_gerencia_usuarios(self):
        self.assertEqual(self.chamar("get", "/api/usuarios", papel="gestor").status_code, 403)
        self.assertEqual(self.chamar("get", "/api/usuarios", papel="operador").status_code, 403)
        r = self.chamar("get", "/api/usuarios", papel="administrador")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.get_json()), 3)

    def test_admin_cria_usuario_e_valida(self):
        corpo = {"nome": "Novo", "email": "novo@teste.com", "senha": "Segura#2026", "papel": "gestor"}
        r = self.chamar("post", "/api/usuarios", corpo, papel="administrador")
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        self.assertEqual(r.get_json()["papel"], "GESTOR")
        self.assertEqual(self.chamar("post", "/api/usuarios", corpo, papel="administrador").status_code, 400)  # duplicado
        ruim = dict(corpo, email="outro@teste.com", senha="123")
        self.assertEqual(self.chamar("post", "/api/usuarios", ruim, papel="administrador").status_code, 400)
        ruim = dict(corpo, email="invalido")
        self.assertEqual(self.chamar("post", "/api/usuarios", ruim, papel="administrador").status_code, 400)
        ruim = dict(corpo, email="x@teste.com", papel="SUPER")
        self.assertEqual(self.chamar("post", "/api/usuarios", ruim, papel="administrador").status_code, 400)

    def test_admin_nao_pode_se_desativar_nem_rebaixar(self):
        meu_id = self.chamar("get", "/api/auth/me", papel="administrador").get_json()["id"]
        r = self.chamar("patch", f"/api/usuarios/{meu_id}", {"ativo": False}, papel="administrador")
        self.assertEqual(r.status_code, 422)
        r = self.chamar("patch", f"/api/usuarios/{meu_id}", {"papel": "OPERADOR"}, papel="administrador")
        self.assertEqual(r.status_code, 422)

    def test_admin_desativa_outro_usuario(self):
        uid = self.chamar("get", "/api/auth/me", papel="operador").get_json()["id"]
        r = self.chamar("patch", f"/api/usuarios/{uid}", {"ativo": False}, papel="administrador")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()["ativo"])


class ProdutoTests(ApiBase):
    def test_gestor_cria_produto_com_estoque_inicial(self):
        r = self.chamar("post", "/api/produtos", {
            "nome": "Ração Canina", "categoria": "Rações Novas", "preco_venda": "189,90",
            "quantidade_atual": 10, "estoque_minimo": 8})
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        c = r.get_json()
        self.assertTrue(c["sku"].startswith("PRD"))
        self.assertEqual(c["quantidade_atual"], 10)
        self.assertEqual(c["preco_venda"], "189.90")
        mov = self.db.execute("SELECT * FROM movimentacao WHERE produto_id=?", (c["id"],)).fetchall()
        self.assertEqual(len(mov), 1)
        self.assertEqual(mov[0]["motivo"], "ESTOQUE_INICIAL")
        self.assertEqual(mov[0]["saldo_apos"], 10)

    def test_operador_nao_cria_produto(self):
        r = self.chamar("post", "/api/produtos", {"nome": "X", "categoria": "Y", "preco_venda": "1"},
                        papel="operador")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.get_json()["erro"]["codigo"], "ACESSO_NEGADO")

    def test_validacoes(self):
        base = {"nome": "X", "categoria": "Y"}
        r = self.chamar("post", "/api/produtos", base)
        self.assertEqual(r.status_code, 400)
        self.assertIn("preco_venda", r.get_json()["erro"]["detalhes"])
        for extra in ({"preco_venda": "-5"}, {"preco_venda": "abc"}, {"preco_venda": "1", "estoque_minimo": -1},
                      {"preco_venda": "1", "quantidade_atual": 1.5}, {"preco_venda": "1e99999"},
                      {"preco_venda": "1", "fornecedor_id": 999}, {"preco_venda": "1", "nome": "x" * 200}):
            r = self.chamar("post", "/api/produtos", {**base, **extra})
            self.assertEqual(r.status_code, 400, extra)

    def test_sku_duplicado_ignora_caixa(self):
        self.produto(sku="DUP")
        r = self.chamar("post", "/api/produtos", {"nome": "Outro", "categoria": "Rações",
                                                   "preco_venda": "5", "sku": "dup"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("sku", r.get_json()["erro"]["detalhes"])

    def test_falha_na_criacao_nao_deixa_lixo(self):
        self.produto(sku="DUP")
        self.chamar("post", "/api/produtos", {"nome": "O", "categoria": "CategoriaFantasma",
                                               "preco_venda": "5", "sku": "DUP"})
        existe = self.db.execute("SELECT 1 FROM categoria WHERE nome='CategoriaFantasma'").fetchone()
        self.assertIsNone(existe)

    def test_listagem_busca_sem_acento_e_filtro_de_situacao(self):
        self.produto(saldo=2, minimo=5, sku="CRIT")
        self.produto(saldo=7, minimo=5, sku="ATEN")
        self.produto(saldo=50, minimo=5, sku="OK")
        for sit, esperado in (("CRITICO", "CRIT"), ("ATENCAO", "ATEN"), ("NORMAL", "OK")):
            skus = [p["sku"] for p in self.chamar("get", f"/api/produtos?situacao={sit}").get_json()["resultados"]]
            self.assertEqual(skus, [esperado], sit)
        self.assertEqual(self.chamar("get", "/api/produtos?q=ATEN").get_json()["total"], 1)
        self.assertEqual(self.chamar("get", "/api/produtos?q=racoes").get_json()["total"], 3)  # categoria "Rações"
        self.assertEqual(self.chamar("get", "/api/produtos?q=%25").get_json()["total"], 0)      # curinga escapado
        self.assertEqual(self.chamar("get", "/api/produtos?situacao=XYZ").status_code, 400)

    def test_paginacao(self):
        for i in range(5):
            self.produto(sku=f"S{i}")
        d = self.chamar("get", "/api/produtos?page_size=2&page=3").get_json()
        self.assertEqual((d["total"], d["paginas"], len(d["resultados"])), (5, 3, 1))
        self.assertEqual(self.chamar("get", "/api/produtos?page=abc").status_code, 400)

    def test_patch_nao_altera_saldo(self):
        pid = self.produto(saldo=20)
        r = self.chamar("patch", f"/api/produtos/{pid}", {"estoque_minimo": 9, "quantidade_atual": 999})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["estoque_minimo"], 9)
        self.assertEqual(self.saldo(pid), 20)

    def test_put_exige_campos_obrigatorios(self):
        pid = self.produto()
        self.assertEqual(self.chamar("put", f"/api/produtos/{pid}", {"nome": "Só nome"}).status_code, 400)
        r = self.chamar("put", f"/api/produtos/{pid}", {"nome": "Novo", "categoria": "Pet",
                                                         "preco_venda": "12,50", "estoque_minimo": 3})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["categoria"], "Pet")

    def test_delete_desativa_e_preserva_historico(self):
        pid = self.produto()
        servicos.registrar_movimentacao(self.db, pid, "SAIDA", "VENDA", 1)
        self.assertEqual(self.chamar("delete", f"/api/produtos/{pid}").status_code, 200)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM movimentacao WHERE produto_id=?", (pid,)).fetchone()[0], 1)
        self.assertEqual(self.chamar("get", "/api/produtos").get_json()["total"], 0)
        self.assertEqual(self.chamar("get", "/api/produtos?ativo=false").get_json()["total"], 1)

    def test_produto_inexistente(self):
        self.assertEqual(self.chamar("get", "/api/produtos/9999").status_code, 404)

    def test_analise_do_produto(self):
        pid = self.produto(saldo=4, minimo=8)
        c = self.chamar("get", f"/api/produtos/{pid}/analise").get_json()
        self.assertEqual(c["analise"]["nivel"], "CRITICO")
        self.assertEqual(len(c["vendas_diarias"]), 30)


class MovimentacaoTests(ApiBase):
    def mov(self, pid, tipo, qtd, motivo=None, papel="gestor"):
        corpo = {"produto_id": pid, "tipo": tipo, "quantidade": qtd}
        if motivo:
            corpo["motivo"] = motivo
        return self.chamar("post", "/api/movimentacoes", corpo, papel=papel)

    def test_entrada_aumenta_saldo(self):
        pid = self.produto(saldo=10)
        r = self.mov(pid, "ENTRADA", 5)
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        self.assertEqual(r.get_json()["saldo_apos"], 15)
        self.assertEqual(self.saldo(pid), 15)

    def test_saida_reduz_saldo_registra_preco_e_usuario(self):
        pid = self.produto(saldo=10, preco_centavos=2500)
        r = self.mov(pid, "SAIDA", 4, "VENDA", papel="operador")
        self.assertEqual(r.status_code, 201)
        c = r.get_json()
        self.assertEqual((c["saldo_apos"], c["valor_unitario"], c["usuario"]), (6, "25.00", "operador@teste.com"))

    def test_saida_maior_que_saldo_e_rejeitada_sem_efeitos(self):
        pid = self.produto(saldo=3)
        r = self.mov(pid, "SAIDA", 4, "VENDA")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.get_json()["erro"]["codigo"], "ESTOQUE_INSUFICIENTE")
        self.assertEqual(self.saldo(pid), 3)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM movimentacao").fetchone()[0], 0)

    def test_motivo_incompativel_e_inativo(self):
        pid = self.produto()
        r = self.mov(pid, "ENTRADA", 1, "VENDA")
        self.assertEqual((r.status_code, r.get_json()["erro"]["codigo"]), (422, "MOTIVO_INCOMPATIVEL"))
        ina = self.produto(sku="INA", ativo=0)
        r = self.mov(ina, "ENTRADA", 1)
        self.assertEqual((r.status_code, r.get_json()["erro"]["codigo"]), (422, "PRODUTO_INATIVO"))

    def test_entradas_invalidas(self):
        pid = self.produto()
        for q in (0, -3, "abc", 1.5, 10 ** 12):
            self.assertEqual(self.mov(pid, "ENTRADA", q).status_code, 400, q)
        r = self.chamar("post", "/api/movimentacoes", {"produto_id": pid, "tipo": "TROCA", "quantidade": 1})
        self.assertEqual(r.status_code, 400)
        r = self.chamar("post", "/api/movimentacoes", {"produto_id": 9999, "tipo": "ENTRADA", "quantidade": 1})
        self.assertEqual(r.status_code, 422)

    def test_saldo_sempre_igual_a_entradas_menos_saidas(self):
        pid = self.produto(saldo=0)
        for tipo, qtd, motivo in (("ENTRADA", 30, "COMPRA"), ("SAIDA", 7, "VENDA"),
                                  ("SAIDA", 3, "PERDA"), ("ENTRADA", 2, "DEVOLUCAO_CLIENTE")):
            self.assertEqual(self.mov(pid, tipo, qtd, motivo).status_code, 201)
        ent = self.db.execute("SELECT SUM(quantidade) FROM movimentacao WHERE tipo='ENTRADA'").fetchone()[0]
        sai = self.db.execute("SELECT SUM(quantidade) FROM movimentacao WHERE tipo='SAIDA'").fetchone()[0]
        self.assertEqual(self.saldo(pid), ent - sai)
        self.assertEqual(self.saldo(pid), 22)

    def test_listagem_com_filtros(self):
        pid = self.produto(saldo=10)
        self.mov(pid, "ENTRADA", 1)
        self.mov(pid, "SAIDA", 1, "VENDA")
        self.assertEqual(self.chamar("get", "/api/movimentacoes?tipo=SAIDA").get_json()["total"], 1)
        self.assertEqual(self.chamar("get", f"/api/movimentacoes?produto={pid}").get_json()["total"], 2)
        hoje = util.hoje_local().isoformat()
        self.assertEqual(self.chamar("get", f"/api/movimentacoes?data_inicio={hoje}&data_fim={hoje}").get_json()["total"], 2)
        self.assertEqual(self.chamar("get", "/api/movimentacoes?data_inicio=ontem").status_code, 400)

    def test_livro_e_imutavel_no_banco(self):
        pid = self.produto()
        servicos.registrar_movimentacao(self.db, pid, "ENTRADA", "COMPRA", 1)
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE movimentacao SET quantidade = 99")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM movimentacao")
        with triggers_suspensos(self.db):  # limpeza administrativa controlada
            self.db.execute("DELETE FROM movimentacao")
        with self.assertRaises(sqlite3.DatabaseError):  # triggers restaurados
            servicos.registrar_movimentacao(self.db, pid, "ENTRADA", "COMPRA", 1)
            self.db.execute("DELETE FROM movimentacao")

    def test_banco_rejeita_motivo_incompativel(self):
        pid = self.produto()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO movimentacao (produto_id,tipo,motivo,quantidade,saldo_apos) "
                            "VALUES (?, 'ENTRADA', 'VENDA', 1, 1)", (pid,))

    def test_transacao_faz_rollback_em_erro(self):
        pid = self.produto(saldo=5)
        with self.assertRaises(Exception):
            from agroestoque.db import transacao
            with transacao(self.db):
                self.db.execute("UPDATE produto SET quantidade_atual = 99 WHERE id = ?", (pid,))
                raise RuntimeError("falha simulada")
        self.assertEqual(self.saldo(pid), 5)


class RecomendacaoTests(ApiBase):
    def pendentes(self, pid):
        return self.db.execute("SELECT * FROM recomendacao WHERE produto_id=? AND status='PENDENTE'", (pid,)).fetchall()

    def test_saida_que_leva_abaixo_do_minimo_gera_recomendacao(self):
        pid = self.produto(saldo=20, minimo=5)
        servicos.registrar_movimentacao(self.db, pid, "SAIDA", "VENDA", 16)
        rec = self.pendentes(pid)
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0]["nivel"], "CRITICO")
        self.assertGreater(rec[0]["quantidade_sugerida"], 0)
        self.assertTrue(rec[0]["justificativa"])

    def test_reposicao_expira_a_recomendacao(self):
        pid = self.produto(saldo=20, minimo=5)
        servicos.registrar_movimentacao(self.db, pid, "SAIDA", "VENDA", 16)
        servicos.registrar_movimentacao(self.db, pid, "ENTRADA", "COMPRA", 200)
        self.assertEqual(self.pendentes(pid), [])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM recomendacao WHERE status='EXPIRADA'").fetchone()[0], 1)

    def test_nao_duplica_recomendacao_pendente(self):
        pid = self.produto(saldo=20, minimo=5)
        servicos.registrar_movimentacao(self.db, pid, "SAIDA", "VENDA", 16)
        servicos.registrar_movimentacao(self.db, pid, "SAIDA", "VENDA", 1)
        servicos.gerar_recomendacoes(self.db)
        self.assertEqual(len(self.pendentes(pid)), 1)

    def test_gerar_usa_historico_e_prazo_do_fornecedor(self):
        fid = self.db.execute("INSERT INTO fornecedor (nome, prazo_entrega_dias) VALUES ('F', 10)").lastrowid
        pid = self.produto(saldo=15, minimo=2)
        self.db.execute("UPDATE produto SET fornecedor_id=? WHERE id=?", (fid, pid))
        agora = util.agora_utc()
        for i in range(1, 11):  # 3 un/dia: demanda ~1,7/dia => cobertura ~9 dias < prazo de 10
            self.db.execute(
                "INSERT INTO movimentacao (produto_id,tipo,motivo,quantidade,saldo_apos,data) "
                "VALUES (?, 'SAIDA', 'VENDA', 3, 15, ?)", (pid, util.para_db(agora - timedelta(days=i))))
        r = self.chamar("post", "/api/recomendacoes/gerar", {})
        self.assertEqual(r.status_code, 200)
        itens = self.chamar("get", "/api/recomendacoes").get_json()["resultados"]
        self.assertEqual([i["produto_id"] for i in itens], [pid])
        self.assertEqual(itens[0]["nivel"], "CRITICO")

    def test_operador_nao_gera_nem_decide_mas_consulta(self):
        pid = self.produto(saldo=1, minimo=5)
        servicos.gerar_recomendacoes(self.db)
        rid = self.pendentes(pid)[0]["id"]
        self.assertEqual(self.chamar("post", "/api/recomendacoes/gerar", {}, papel="operador").status_code, 403)
        self.assertEqual(self.chamar("post", f"/api/recomendacoes/{rid}/decidir", {"status": "ACEITA"}, papel="operador").status_code, 403)
        self.assertEqual(self.chamar("get", "/api/recomendacoes", papel="operador").status_code, 200)

    def test_gestor_decide_uma_unica_vez(self):
        pid = self.produto(saldo=1, minimo=5)
        servicos.gerar_recomendacoes(self.db)
        rid = self.pendentes(pid)[0]["id"]
        r = self.chamar("post", f"/api/recomendacoes/{rid}/decidir", {"status": "aceita"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.get_json()["status"], r.get_json()["decidida_por"]), ("ACEITA", "gestor@teste.com"))
        r = self.chamar("post", f"/api/recomendacoes/{rid}/decidir", {"status": "IGNORADA"})
        self.assertEqual((r.status_code, r.get_json()["erro"]["codigo"]), (422, "RECOMENDACAO_JA_DECIDIDA"))

    def test_status_invalido_e_inexistente(self):
        pid = self.produto(saldo=1, minimo=5)
        servicos.gerar_recomendacoes(self.db)
        rid = self.pendentes(pid)[0]["id"]
        self.assertEqual(self.chamar("post", f"/api/recomendacoes/{rid}/decidir", {"status": "TALVEZ"}).status_code, 422)
        self.assertEqual(self.chamar("post", "/api/recomendacoes/9999/decidir", {"status": "ACEITA"}).status_code, 422)
        self.assertEqual(self.chamar("get", "/api/recomendacoes?status=XPTO").status_code, 400)

    def test_decisao_recente_evita_insistencia(self):
        pid = self.produto(saldo=1, minimo=5)
        servicos.gerar_recomendacoes(self.db)
        servicos.decidir_recomendacao(self.db, self.pendentes(pid)[0]["id"], "IGNORADA", 1)
        servicos.gerar_recomendacoes(self.db)
        self.assertEqual(self.pendentes(pid), [])

    def test_desativar_produto_expira_recomendacao(self):
        pid = self.produto(saldo=1, minimo=5)
        servicos.gerar_recomendacoes(self.db)
        self.chamar("delete", f"/api/produtos/{pid}")
        self.assertEqual(self.pendentes(pid), [])


class DashboardEOutrosTests(ApiBase):
    def test_dashboard(self):
        a = self.produto(saldo=50, minimo=5, sku="A", preco_centavos=1000)
        self.produto(saldo=2, minimo=5, sku="B")
        servicos.registrar_movimentacao(self.db, a, "SAIDA", "VENDA", 10)
        d = self.chamar("get", "/api/dashboard").get_json()
        self.assertEqual((d["total_produtos"], d["itens_criticos"], d["vendas_mes_unidades"]), (2, 1, 10))
        self.assertEqual(d["faturamento_mes"], "100.00")
        self.assertEqual(len(d["saidas_ultimos_7_dias"]), 7)
        self.assertEqual(d["saidas_ultimos_7_dias"][-1]["quantidade"], 10)
        self.assertEqual(d["produtos_mais_vendidos"][0]["quantidade"], 10)

    def test_dashboard_vazio(self):
        d = self.chamar("get", "/api/dashboard").get_json()
        self.assertEqual((d["total_produtos"], d["vendas_mes_unidades"], d["faturamento_mes"]), (0, 0, "0.00"))
        self.assertIsNone(d["variacao_vendas_percentual"])

    def test_categorias_e_fornecedores(self):
        r = self.chamar("post", "/api/fornecedores", {"nome": "Forn X", "prazo_entrega_dias": 5})
        self.assertEqual(r.status_code, 201)
        fid = r.get_json()["id"]
        self.assertEqual(self.chamar("post", "/api/fornecedores", {"nome": "forn x"}).status_code, 400)
        r = self.chamar("put", f"/api/fornecedores/{fid}", {"nome": "Forn Y", "prazo_entrega_dias": 9})
        self.assertEqual(r.get_json()["prazo_entrega_dias"], 9)
        self.assertEqual(self.chamar("post", "/api/fornecedores", {"nome": "Z"}, papel="operador").status_code, 403)
        self.assertEqual(self.chamar("post", "/api/fornecedores", {"nome": "W", "prazo_entrega_dias": 0}).status_code, 400)
        self.assertEqual(self.chamar("delete", f"/api/fornecedores/{fid}").get_json()["ativo"], False)
        self.assertEqual(self.chamar("post", "/api/categorias", {"nome": "Nova"}).status_code, 201)
        self.assertEqual(self.chamar("post", "/api/categorias", {"nome": "nova"}).status_code, 200)
        self.assertIn("Nova", [c["nome"] for c in self.chamar("get", "/api/categorias").get_json()])

    def test_paginas_html_e_documentacao(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/api-docs").status_code, 200)
        r = self.client.get("/api-docs/openapi.yaml")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"openapi: 3.0.3", r.data)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)

    def test_erro_inesperado_vira_json_500(self):
        from agroestoque import servicos as sv
        original = sv.montar_dashboard
        sv.montar_dashboard = lambda *a, **k: 1 / 0
        try:
            self.app.config["PROPAGATE_EXCEPTIONS"] = False
            r = self.chamar("get", "/api/dashboard")
        finally:
            sv.montar_dashboard = original
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.get_json()["erro"]["codigo"], "ERRO_INTERNO")


if __name__ == "__main__":
    unittest.main()
