"""Endpoints da API REST do AgroEstoque (JSON), registrados em /api."""
from datetime import datetime, timedelta

from flask import Blueprint, current_app, g, jsonify, request

from . import agente, analise, auth, google, servicos, serializers as s, util, validacao as v
from .auth import ADMINISTRADOR, GESTAO, protegido
from .db import get_db
from .erros import ApiError, acesso_negado, erro_campo, nao_encontrado, regra

bp = Blueprint("api", __name__, url_prefix="/api")


# ------------------------------------------------------------------ saúde
@bp.get("/saude")
def saude():
    return jsonify(status="ok", servico="AgroEstoque API", versao="3.0")


# -------------------------------------------------------------- autenticação
@bp.post("/auth/login")
def login():
    dados = v.ler_json()
    email = v.texto(dados, "email", max_len=254).lower()
    senha = dados.get("senha")
    if not isinstance(senha, str) or not senha:
        raise erro_campo("senha", "Este campo é obrigatório.")

    limitador = current_app.extensions["limitador_login"]
    if limitador.bloqueado(email):
        raise ApiError(429, "MUITAS_TENTATIVAS",
                       "Muitas tentativas de login. Aguarde 15 minutos e tente novamente.")
    db = get_db()
    usuario = db.execute("SELECT * FROM usuario WHERE email = ?", (email,)).fetchone()
    # compara sempre um hash, para não revelar (pelo tempo) se o e-mail existe
    hash_ref = usuario["senha_hash"] if usuario else current_app.config["_HASH_FALSO"]
    confere = auth.senha_confere(hash_ref, senha)
    if usuario is None or not usuario["ativo"] or not confere:
        limitador.falha(email)
        current_app.logger.warning("Falha de login para %s", email)
        raise ApiError(401, "CREDENCIAIS_INVALIDAS", "E-mail ou senha incorretos.")
    limitador.sucesso(email)
    return jsonify(token=auth.gerar_token(usuario), tipo="Bearer",
                   expira_em_segundos=current_app.config["TOKEN_TTL_SEGUNDOS"],
                   usuario=s.usuario(usuario))


@bp.get("/auth/me")
@protegido()
def me():
    return jsonify(s.usuario(g.usuario))


@bp.get("/auth/config")
def config_publica():
    """Configuração que a tela de login precisa antes de autenticar (nada sigiloso)."""
    cfg = current_app.config
    return jsonify(google_client_id=cfg.get("GOOGLE_CLIENT_ID") or None, agente_ia=agente.configurado())


@bp.post("/auth/google")
def login_google():
    """Entrar com a conta Google. Só entra quem já tem usuário ativo com o mesmo e-mail."""
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ApiError(503, "GOOGLE_NAO_CONFIGURADO", "O login com Google não está ativado neste servidor.")
    credential = v.texto(v.ler_json(), "credential", max_len=4096)
    try:
        info = google.verificar(credential, client_id)
    except google.TokenGoogleInvalido as e:
        current_app.logger.warning("Login Google recusado: %s", e)
        raise ApiError(401, "TOKEN_GOOGLE_INVALIDO", "Não foi possível validar a sua conta Google. Tente novamente.")
    except google.GoogleIndisponivel as e:
        current_app.logger.error("Login Google: Google inacessível (%s)", e)
        raise ApiError(503, "GOOGLE_INDISPONIVEL",
                       "Não foi possível falar com o Google agora. Entre com e-mail e senha ou tente de novo.")
    usuario = get_db().execute("SELECT * FROM usuario WHERE email = ?", (info["email"],)).fetchone()
    if usuario is None or not usuario["ativo"]:
        current_app.logger.warning("Login Google de conta não autorizada: %s", info["email"])
        raise ApiError(403, "CONTA_NAO_AUTORIZADA",
                       f"A conta {info['email']} não está autorizada. Peça ao administrador para cadastrar este e-mail.")
    return jsonify(token=auth.gerar_token(usuario), tipo="Bearer",
                   expira_em_segundos=current_app.config["TOKEN_TTL_SEGUNDOS"],
                   usuario=s.usuario(usuario))


@bp.post("/auth/alterar-senha")
@protegido()
def alterar_senha():
    d = v.ler_json()
    atual, nova = d.get("senha_atual"), d.get("nova_senha")
    if not isinstance(atual, str) or not auth.senha_confere(g.usuario["senha_hash"], atual):
        raise erro_campo("senha_atual", "Senha atual incorreta.")
    v.validar_senha(nova, "nova_senha")
    db = get_db()
    db.execute("UPDATE usuario SET senha_hash = ? WHERE id = ?", (auth.hash_senha(nova), g.usuario["id"]))
    return jsonify(mensagem="Senha alterada. Faça login novamente.")


# ------------------------------------------------------------------ usuários
@bp.get("/usuarios")
@protegido(ADMINISTRADOR)
def usuarios_listar():
    linhas = get_db().execute("SELECT * FROM usuario ORDER BY nome COLLATE NOCASE").fetchall()
    return jsonify([s.usuario(u) for u in linhas])


@bp.post("/usuarios")
@protegido(ADMINISTRADOR)
def usuarios_criar():
    d = v.ler_json()
    uid = servicos.criar_usuario(
        get_db(), v.texto(d, "nome", max_len=120), v.email(d), v.validar_senha(d.get("senha")),
        v.texto(d, "papel", obrigatorio=False, padrao=auth.OPERADOR).upper())
    return jsonify(s.usuario(servicos.buscar_usuario(get_db(), uid))), 201


@bp.patch("/usuarios/<int:uid>")
@protegido(ADMINISTRADOR)
def usuarios_atualizar(uid):
    db = get_db()
    alvo = servicos.buscar_usuario(db, uid)
    d = v.ler_json()
    sets, params = [], []
    if "nome" in d:
        sets.append("nome = ?"); params.append(v.texto(d, "nome", max_len=120))
    if "papel" in d:
        papel = v.texto(d, "papel").upper()
        if papel not in auth.PAPEIS:
            raise erro_campo("papel", f"Use um destes valores: {', '.join(auth.PAPEIS)}.")
        if uid == g.usuario["id"] and papel != alvo["papel"]:
            raise regra("AUTO_ALTERACAO", "Você não pode alterar o seu próprio perfil de acesso.")
        sets.append("papel = ?"); params.append(papel)
    if "ativo" in d:
        if not isinstance(d["ativo"], bool):
            raise erro_campo("ativo", "Deve ser true ou false.")
        if uid == g.usuario["id"] and not d["ativo"]:
            raise regra("AUTO_ALTERACAO", "Você não pode desativar o seu próprio usuário.")
        sets.append("ativo = ?"); params.append(int(d["ativo"]))
    if "senha" in d:
        sets.append("senha_hash = ?"); params.append(auth.hash_senha(v.validar_senha(d["senha"])))
    if not sets:
        raise ApiError(400, "DADOS_INVALIDOS", "Nenhum campo para atualizar.")
    db.execute(f"UPDATE usuario SET {', '.join(sets)} WHERE id = ?", (*params, uid))
    return jsonify(s.usuario(servicos.buscar_usuario(db, uid)))


# ------------------------------------------------------------ agente de IA
def _resposta_agente(produto, ja_existia, confianca=None, quantidade=0):
    p = s.produto(produto)
    aviso = []
    if ja_existia:
        msg = f"\"{p['nome']}\" já estava cadastrado. Nada foi duplicado."
        if quantidade:
            aviso.append("A quantidade informada não foi lançada; registre a entrada em Movimentações.")
    else:
        msg = f"Produto \"{p['nome']}\" cadastrado."
        if p["preco_venda"] in (0, 0.0, "0.00", "0"):
            aviso.append("Preço a definir: não havia etiqueta legível.")
        if confianca == "baixa":
            aviso.append("Confiança baixa: confira os dados.")
    resp = jsonify(produto=p, ja_existia=ja_existia, confianca=confianca, avisos=aviso, mensagem=msg)
    resp.status_code = 200 if ja_existia else 201
    return resp


@bp.post("/agente/foto")
@protegido()
def agente_foto():
    """Recebe a foto de um produto (multipart, campo 'foto'); o agente de IA o identifica e cadastra."""
    cfg = current_app.config
    limite = cfg["AGENTE_MAX_FOTO_BYTES"]
    request.max_content_length = limite + 200_000     # fotos passam do limite padrão de 1 MB
    if not agente.configurado():
        raise ApiError(503, "AGENTE_NAO_CONFIGURADO",
                       "O agente de IA ainda não foi ativado neste servidor. Avise o administrador.")
    arquivo = request.files.get("foto")
    if arquivo is None:
        raise erro_campo("foto", "Envie a foto no campo 'foto' (multipart/form-data).")
    imagem = arquivo.read(limite + 1)
    if len(imagem) > limite:
        raise ApiError(413, "FOTO_MUITO_GRANDE", f"A foto passa de {limite // 1_000_000} MB.")
    tipo = agente.detectar_tipo(imagem)
    if tipo is None:
        raise ApiError(415, "TIPO_NAO_SUPORTADO", "Envie uma imagem JPEG, PNG, WEBP ou GIF.")
    quantidade = v.inteiro(request.form, "quantidade", obrigatorio=False, minimo=0, padrao=0)
    if not current_app.extensions["limite_fotos"].permitir(g.usuario["id"], cfg["AGENTE_FOTOS_POR_MINUTO"]):
        raise ApiError(429, "MUITAS_FOTOS", "Muitas fotos em pouco tempo. Aguarde um minuto.")
    db = get_db()
    saida = agente.consultar_modelo(imagem, tipo, agente.categorias_existentes(db))
    campos = agente.normalizar(saida)
    produto, ja_existia = agente.cadastrar(db, campos, g.usuario["id"], quantidade)
    current_app.logger.info("Agente de IA: produto %s (%s) por %s", produto["id"],
                            "já existia" if ja_existia else "cadastrado", g.usuario["email"])
    return _resposta_agente(produto, ja_existia, campos["confianca"], quantidade)


@bp.post("/agente/produtos")
@protegido()
def agente_produtos():
    """Cadastro estruturado para agentes externos (servidor MCP: WhatsApp, Telegram etc.).

    Mesmas regras da foto: nunca duplica, preço opcional, qualquer perfil autenticado.
    """
    d = v.ler_json()
    campos = agente.normalizar({
        "identificado": True, "nome": v.texto(d, "nome", max_len=150),
        "categoria": v.texto(d, "categoria", obrigatorio=False, max_len=80, padrao="Outros"),
        "unidade": v.texto(d, "unidade", obrigatorio=False, max_len=20, padrao="unidade"),
        "preco_venda": d.get("preco_venda"), "codigo_barras": d.get("codigo_barras"), "confianca": "alta"})
    quantidade = v.inteiro(d, "quantidade", obrigatorio=False, minimo=0, padrao=0)
    produto, ja_existia = agente.cadastrar(get_db(), campos, g.usuario["id"], quantidade)
    return _resposta_agente(produto, ja_existia, None, quantidade)


# ---------------------------------------------------------------- categorias
@bp.get("/categorias")
@protegido()
def categorias_listar():
    linhas = get_db().execute("SELECT * FROM categoria ORDER BY nome COLLATE NOCASE")
    return jsonify([s.categoria(c) for c in linhas])


@bp.post("/categorias")
@protegido(*GESTAO)
def categorias_criar():
    nome = v.texto(v.ler_json(), "nome", max_len=80)
    db = get_db()
    cid, criada = servicos.obter_ou_criar_categoria(db, nome)
    return jsonify(s.categoria(db.execute("SELECT * FROM categoria WHERE id = ?", (cid,)).fetchone())), (
        201 if criada else 200)


# -------------------------------------------------------------- fornecedores
def _dados_fornecedor(d):
    return (v.texto(d, "nome", max_len=120), v.texto(d, "telefone", obrigatorio=False, max_len=30),
            v.texto(d, "email", obrigatorio=False, max_len=254),
            v.inteiro(d, "prazo_entrega_dias", obrigatorio=False, minimo=1, padrao=7, maximo=365))


def _fornecedor(db, fid):
    f = db.execute("SELECT * FROM fornecedor WHERE id = ?", (fid,)).fetchone()
    if f is None:
        raise nao_encontrado("Fornecedor não encontrado.")
    return f


@bp.get("/fornecedores")
@protegido()
def fornecedores_listar():
    linhas = get_db().execute("SELECT * FROM fornecedor ORDER BY nome COLLATE NOCASE")
    return jsonify([s.fornecedor(f) for f in linhas])


@bp.post("/fornecedores")
@protegido(*GESTAO)
def fornecedores_criar():
    nome, tel, email, prazo = _dados_fornecedor(v.ler_json())
    db = get_db()
    if db.execute("SELECT 1 FROM fornecedor WHERE nome = ?", (nome,)).fetchone():
        raise erro_campo("nome", "Já existe um fornecedor com este nome.")
    fid = db.execute("INSERT INTO fornecedor (nome, telefone, email, prazo_entrega_dias) VALUES (?,?,?,?)",
                     (nome, tel, email, prazo)).lastrowid
    return jsonify(s.fornecedor(_fornecedor(db, fid))), 201


@bp.get("/fornecedores/<int:fid>")
@protegido()
def fornecedores_detalhe(fid):
    return jsonify(s.fornecedor(_fornecedor(get_db(), fid)))


@bp.put("/fornecedores/<int:fid>")
@protegido(*GESTAO)
def fornecedores_atualizar(fid):
    db = get_db()
    _fornecedor(db, fid)
    nome, tel, email, prazo = _dados_fornecedor(v.ler_json())
    if db.execute("SELECT 1 FROM fornecedor WHERE nome = ? AND id <> ?", (nome, fid)).fetchone():
        raise erro_campo("nome", "Já existe um fornecedor com este nome.")
    db.execute("UPDATE fornecedor SET nome=?, telefone=?, email=?, prazo_entrega_dias=? WHERE id=?",
               (nome, tel, email, prazo, fid))
    return jsonify(s.fornecedor(_fornecedor(db, fid)))


@bp.delete("/fornecedores/<int:fid>")
@protegido(*GESTAO)
def fornecedores_desativar(fid):
    db = get_db()
    _fornecedor(db, fid)
    db.execute("UPDATE fornecedor SET ativo = 0 WHERE id = ?", (fid,))
    return jsonify(s.fornecedor(_fornecedor(db, fid)))


# ------------------------------------------------------------------ produtos
@bp.get("/produtos")
@protegido()
def produtos_listar():
    db = get_db()
    where, params = [], []
    ativo = request.args.get("ativo", "true").lower()
    if ativo in ("true", "1"):
        where.append("p.ativo = 1")
    elif ativo in ("false", "0"):
        where.append("p.ativo = 0")
    q = request.args.get("q", "").strip()
    if q:
        where.append("(sem_acento(p.nome) LIKE ? ESCAPE '\\' OR sem_acento(p.sku) LIKE ? ESCAPE '\\' "
                     "OR sem_acento(c.nome) LIKE ? ESCAPE '\\')")
        params += [servicos.like(q)] * 3
    cat = request.args.get("categoria", "").strip()
    if cat:
        where.append("c.nome = ?")
        params.append(cat)
    sit = request.args.get("situacao", "").strip().upper()
    if sit:
        if sit not in servicos.FILTROS_SITUACAO:
            raise ApiError(400, "PARAMETRO_INVALIDO", "situacao deve ser CRITICO, ATENCAO ou NORMAL.")
        where.append(servicos.FILTROS_SITUACAO[sit])
    corpo = servicos.SQL_FROM_PRODUTO
    if where:
        corpo += " WHERE " + " AND ".join(where)
    pagina, tamanho = v.pagina_params(50)
    total = db.execute(f"SELECT COUNT(*) {corpo}", params).fetchone()[0]
    linhas = db.execute(
        f"{servicos.SQL_COLUNAS_PRODUTO} {corpo} ORDER BY sem_acento(p.nome) LIMIT ? OFFSET ?", (*params, tamanho, (pagina - 1) * tamanho))
    return jsonify({"resultados": [s.produto(p) for p in linhas], "total": total, "pagina": pagina,
                    "paginas": max(1, -(-total // tamanho)), "tamanho_pagina": tamanho})


@bp.post("/produtos")
@protegido(*GESTAO)
def produtos_criar():
    d = v.ler_json()
    fid = d.get("fornecedor_id")
    dados = {
        "nome": v.texto(d, "nome", max_len=150),
        "sku": v.texto(d, "sku", obrigatorio=False, max_len=30),
        "categoria": v.texto(d, "categoria", max_len=80),
        "unidade": v.texto(d, "unidade", obrigatorio=False, max_len=20, padrao="unidade") or "unidade",
        "preco_centavos": v.dinheiro(d, "preco_venda"),
        "estoque_minimo": v.inteiro(d, "estoque_minimo", obrigatorio=False, minimo=0),
        "quantidade_inicial": v.inteiro(d, "quantidade_atual", obrigatorio=False, minimo=0),
        "fornecedor_id": v.inteiro({"x": fid}, "x", obrigatorio=False, minimo=1, padrao=None) if fid not in (None, "") else None,
    }
    db = get_db()
    pid = servicos.criar_produto(db, dados, usuario_id=g.usuario["id"])
    return jsonify(s.produto(servicos.buscar_produto(db, pid))), 201


@bp.get("/produtos/<int:pid>")
@protegido()
def produtos_detalhe(pid):
    return jsonify(s.produto(servicos.buscar_produto(get_db(), pid)))


def _atualizar_produto(pid, parcial):
    db = get_db()
    servicos.buscar_produto(db, pid)
    d = v.ler_json()
    c = {}
    if "nome" in d or not parcial:
        c["nome"] = v.texto(d, "nome", max_len=150)
    if "sku" in d:
        c["sku"] = v.texto(d, "sku", max_len=30)
    if "categoria" in d or not parcial:
        c["categoria"] = v.texto(d, "categoria", max_len=80)
    if "unidade" in d:
        c["unidade"] = v.texto(d, "unidade", max_len=20)
    if "preco_venda" in d or not parcial:
        c["preco_venda_centavos"] = v.dinheiro(d, "preco_venda")
    if "estoque_minimo" in d or not parcial:
        c["estoque_minimo"] = v.inteiro(d, "estoque_minimo", obrigatorio=not parcial, minimo=0)
    if "fornecedor_id" in d:
        fid = d["fornecedor_id"]
        c["fornecedor_id"] = None if fid in (None, "") else v.inteiro(d, "fornecedor_id", minimo=1)
    if "ativo" in d:
        if not isinstance(d["ativo"], bool):
            raise erro_campo("ativo", "Deve ser true ou false.")
        c["ativo"] = int(d["ativo"])
    # o saldo (quantidade_atual) NUNCA é alterado aqui: somente por movimentações
    return jsonify(s.produto(servicos.atualizar_produto(db, pid, c)))


@bp.put("/produtos/<int:pid>")
@protegido(*GESTAO)
def produtos_substituir(pid):
    return _atualizar_produto(pid, parcial=False)


@bp.patch("/produtos/<int:pid>")
@protegido(*GESTAO)
def produtos_atualizar(pid):
    return _atualizar_produto(pid, parcial=True)


@bp.delete("/produtos/<int:pid>")
@protegido(*GESTAO)
def produtos_desativar(pid):  # exclusão lógica: preserva o histórico
    db = get_db()
    servicos.buscar_produto(db, pid)
    return jsonify(s.produto(servicos.desativar_produto(db, pid)))


@bp.get("/produtos/<int:pid>/analise")
@protegido()
def produtos_analise(pid):
    db = get_db()
    p = servicos.buscar_produto(db, pid)
    series, datas = servicos.series_por_produto(db, [pid])
    serie = series[pid]
    r = servicos.analisar_produto(p, serie)
    return jsonify({
        "produto": s.produto(p),
        "analise": {
            "nivel": r.nivel, "media_recente_14d": r.media_recente, "media_30d": r.media_base,
            "demanda_diaria_prevista": r.demanda_diaria, "dias_cobertura": r.dias_cobertura,
            "tendencia_percentual": r.tendencia_pct, "prazo_entrega_dias": r.prazo_entrega_dias,
            "ponto_de_pedido": r.ponto_de_pedido, "quantidade_sugerida": r.quantidade_sugerida,
            "acao_sugerida": r.acao_sugerida, "justificativa": r.justificativa},
        "vendas_diarias": [{"data": d.isoformat(), "quantidade": q} for d, q in zip(datas, serie)],
    })


# ------------------------------------------------------------- movimentações
def _data_param(nome, fim=False):
    try:
        d = datetime.strptime(request.args[nome], "%Y-%m-%d").date()
    except ValueError:
        raise ApiError(400, "PARAMETRO_INVALIDO", f"{nome} deve estar no formato AAAA-MM-DD.")
    return util.inicio_dia_db(d + timedelta(days=1) if fim else d)


@bp.get("/movimentacoes")
@protegido()
def movimentacoes_listar():
    where, params = [], []
    if request.args.get("produto"):
        try:
            where.append("m.produto_id = ?")
            params.append(int(request.args["produto"]))
        except ValueError:
            raise ApiError(400, "PARAMETRO_INVALIDO", "produto deve ser um número.")
    tipo = request.args.get("tipo", "").upper()
    if tipo:
        if tipo not in servicos.MOTIVOS_POR_TIPO:
            raise ApiError(400, "PARAMETRO_INVALIDO", "tipo deve ser ENTRADA ou SAIDA.")
        where.append("m.tipo = ?")
        params.append(tipo)
    if request.args.get("data_inicio"):
        where.append("m.data >= ?")
        params.append(_data_param("data_inicio"))
    if request.args.get("data_fim"):
        where.append("m.data < ?")
        params.append(_data_param("data_fim", fim=True))
    base = ("FROM movimentacao m JOIN produto p ON p.id = m.produto_id "
            "LEFT JOIN usuario u ON u.id = m.usuario_id")
    if where:
        base += " WHERE " + " AND ".join(where)
    db = get_db()
    pagina, tamanho = v.pagina_params(20)
    total = db.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
    linhas = db.execute(
        f"SELECT m.*, p.nome AS produto, u.email AS usuario {base} ORDER BY m.data DESC, m.id DESC LIMIT ? OFFSET ?",
        (*params, tamanho, (pagina - 1) * tamanho))
    return jsonify({"resultados": [s.movimentacao(m) for m in linhas], "total": total, "pagina": pagina,
                    "paginas": max(1, -(-total // tamanho)), "tamanho_pagina": tamanho})


@bp.post("/movimentacoes")
@protegido()
def movimentacoes_criar():
    d = v.ler_json()
    produto_id = v.inteiro(d, "produto_id", minimo=1)
    tipo = v.texto(d, "tipo", max_len=10).upper()
    if tipo not in servicos.MOTIVOS_POR_TIPO:
        raise erro_campo("tipo", "Use ENTRADA ou SAIDA.")
    motivo = v.texto(d, "motivo", obrigatorio=False, max_len=24).upper() or (
        "COMPRA" if tipo == "ENTRADA" else "VENDA")
    db = get_db()
    mid = servicos.registrar_movimentacao(
        db, produto_id, tipo, motivo, v.inteiro(d, "quantidade", minimo=1),
        usuario_id=g.usuario["id"], observacao=v.texto(d, "observacao", obrigatorio=False, max_len=255),
        valor_unitario_centavos=v.dinheiro(d, "valor_unitario", obrigatorio=False))
    return jsonify(s.movimentacao(servicos.buscar_movimentacao(db, mid))), 201


# ----------------------------------------------------------------- dashboard
@bp.get("/dashboard")
@protegido()
def dashboard():
    return jsonify(servicos.montar_dashboard(get_db()))


# ------------------------------------------------------------- recomendações
@bp.get("/recomendacoes")
@protegido()
def recomendacoes_listar():
    status = request.args.get("status", "PENDENTE").upper()
    sql = ("""SELECT r.*, p.nome AS produto, p.sku AS sku, p.quantidade_atual AS saldo_atual,
                     u.email AS decidida_por
              FROM recomendacao r JOIN produto p ON p.id = r.produto_id
              LEFT JOIN usuario u ON u.id = r.decidida_por_id""")
    params = []
    if status != "TODAS":
        if status not in ("PENDENTE", "ACEITA", "IGNORADA", "EXPIRADA"):
            raise ApiError(400, "PARAMETRO_INVALIDO",
                           "status deve ser PENDENTE, ACEITA, IGNORADA, EXPIRADA ou TODAS.")
        sql += " WHERE r.status = ?"
        params.append(status)
    sql += (" ORDER BY CASE r.nivel WHEN 'CRITICO' THEN 0 ELSE 1 END, (r.dias_cobertura IS NULL),"
            " r.dias_cobertura, r.gerada_em DESC")
    itens = [s.recomendacao(r) for r in get_db().execute(sql, params)]
    return jsonify({"resultados": itens, "total": len(itens)})


@bp.post("/recomendacoes/gerar")
@protegido(*GESTAO)
def recomendacoes_gerar():
    afetadas, pendentes = servicos.gerar_recomendacoes(get_db())
    return jsonify(atualizadas=afetadas, pendentes=pendentes)


@bp.post("/recomendacoes/<int:rid>/decidir")
@protegido(*GESTAO)
def recomendacoes_decidir(rid):
    status = v.texto(v.ler_json(), "status", max_len=10).upper()
    return jsonify(s.recomendacao(servicos.decidir_recomendacao(get_db(), rid, status, g.usuario["id"])))
