"""Autenticação por token assinado (Bearer) e autorização por papel."""
import threading
import time
from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from .erros import ApiError, acesso_negado

SALT = "agroestoque.api.token"
ADMINISTRADOR, GESTOR, OPERADOR = "ADMINISTRADOR", "GESTOR", "OPERADOR"
GESTAO = (ADMINISTRADOR, GESTOR)
PAPEIS = (ADMINISTRADOR, GESTOR, OPERADOR)


def hash_senha(senha):
    return generate_password_hash(
        senha, method=f"pbkdf2:sha256:{current_app.config['PASSWORD_ITERACOES']}")


def senha_confere(senha_hash, senha):
    return check_password_hash(senha_hash, senha)


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT)


def gerar_token(usuario):
    # o fragmento do hash invalida tokens antigos quando a senha é trocada
    return _serializador().dumps({"uid": usuario["id"], "h": usuario["senha_hash"][-16:]})


def usuario_do_token(token):
    from .db import get_db
    try:
        dados = _serializador().loads(token, max_age=current_app.config["TOKEN_TTL_SEGUNDOS"])
    except SignatureExpired:
        raise ApiError(401, "TOKEN_EXPIRADO", "Sessão expirada. Faça login novamente.")
    except BadSignature:
        raise ApiError(401, "TOKEN_INVALIDO", "Token de acesso inválido.")
    usuario = get_db().execute(
        "SELECT * FROM usuario WHERE id = ? AND ativo = 1", (dados.get("uid"),)).fetchone()
    if usuario is None or usuario["senha_hash"][-16:] != dados.get("h"):
        raise ApiError(401, "TOKEN_INVALIDO", "Token de acesso inválido.")
    return usuario


def autenticar():
    partes = request.headers.get("Authorization", "").split()
    if len(partes) != 2 or partes[0].lower() != "bearer":
        raise ApiError(401, "NAO_AUTENTICADO",
                       "Autenticação necessária. Envie 'Authorization: Bearer <token>'.")
    return usuario_do_token(partes[1])


def protegido(*papeis):
    """Exige token válido e, se informados, um dos papéis."""
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            g.usuario = autenticar()
            if papeis and g.usuario["papel"] not in papeis:
                raise acesso_negado(papeis)
            return func(*args, **kwargs)
        return wrapper
    return decorador


def eh_gestao():
    return g.usuario["papel"] in GESTAO


# ------------------------------------------------ bloqueio de tentativas
class LimitadorLogin:
    """Bloqueia o e-mail após N falhas em uma janela de tempo (memória do processo)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._falhas = {}

    def bloqueado(self, chave):
        cfg = current_app.config
        with self._lock:
            registro = self._falhas.get(chave)
            if not registro:
                return False
            qtd, inicio = registro
            if time.time() - inicio > cfg["BLOQUEIO_LOGIN_SEGUNDOS"]:
                del self._falhas[chave]
                return False
            return qtd >= cfg["MAX_TENTATIVAS_LOGIN"]

    def falha(self, chave):
        with self._lock:
            qtd, inicio = self._falhas.get(chave, (0, time.time()))
            self._falhas[chave] = (qtd + 1, inicio)

    def sucesso(self, chave):
        with self._lock:
            self._falhas.pop(chave, None)
