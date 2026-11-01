AgroEstoque – sistema de gestão de estoque com recomendação de reposição (Flask).

import logging
import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from . import auth, db, util
from .config import Config
from .erros import ApiError

CODIGOS_HTTP = {400: "REQUISICAO_INVALIDA", 404: "ROTA_NAO_ENCONTRADA", 405: "METODO_NAO_PERMITIDO",
                413: "CORPO_MUITO_GRANDE", 415: "TIPO_NAO_SUPORTADO"}


def _erro_json(status, codigo, mensagem, detalhes=None):
    resp = jsonify(erro={"codigo": codigo, "mensagem": mensagem, "detalhes": detalhes or {}})
    resp.status_code = status
    return resp


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    # --- segurança: chave secreta ---
    if not app.config.get("SECRET_KEY"):
        if os.environ.get("AGROESTOQUE_PRODUCAO") == "1":
            raise RuntimeError("Defina AGROESTOQUE_SECRET_KEY em produção.")
        # desenvolvimento: chave persistida em instance/ (tokens sobrevivem a reinícios)
        arquivo = Path(app.config["DATABASE"]).parent / ".secret_key"
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        if not arquivo.exists():
            arquivo.write_text(secrets.token_hex(32))
        app.config["SECRET_KEY"] = arquivo.read_text().strip()

    app.json.ensure_ascii = False
    app.json.sort_keys = False
    app.url_map.strict_slashes = False
    logging.basicConfig(level=logging.WARNING if app.config.get("TESTING") else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    util.configurar_fuso(app.config["TIMEZONE"])
    app.config["_HASH_FALSO"] = generate_password_hash(
        "senha-inexistente", method=f"pbkdf2:sha256:{app.config['PASSWORD_ITERACOES']}")
    app.extensions["limitador_login"] = auth.LimitadorLogin()

    # --- banco de dados ---
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(db.close_db)
    with app.app_context():
        conn = db.get_db()
        if not db.banco_inicializado(conn):
            db.init_db(conn)
            app.logger.info("Banco de dados criado em %s", app.config["DATABASE"])

    # --- rotas ---
    from . import api, web, cli
    app.register_blueprint(api.bp)
    app.register_blueprint(web.bp)
    cli.registrar(app)

    # --- tratamento de erros (JSON em /api) ---
    @app.errorhandler(ApiError)
    def tratar_api_error(e):
        return _erro_json(e.status, e.codigo, e.mensagem, e.detalhes)

    @app.errorhandler(HTTPException)
    def tratar_http(e):
        if request.path.startswith("/api"):
            return _erro_json(e.code, CODIGOS_HTTP.get(e.code, "ERRO_HTTP"), e.description)
        return e

    @app.errorhandler(Exception)
    def tratar_inesperado(e):
        import sqlite3
        if not request.path.startswith("/api"):
            raise e
        if isinstance(e, sqlite3.IntegrityError):
            app.logger.warning("Violação de integridade: %s", e)
            return _erro_json(409, "CONFLITO_DADOS", "Os dados enviados violam uma restrição do banco.")
        app.logger.exception("Erro inesperado em %s %s", request.method, request.path)
        return _erro_json(500, "ERRO_INTERNO", "Erro interno do servidor.")

    @app.after_request
    def cabecalhos_seguranca(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/api"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    return app
