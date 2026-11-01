import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class Config:
    """Configuração padrão (desenvolvimento). Variáveis de ambiente:

    AGROESTOQUE_SECRET_KEY, AGROESTOQUE_DATABASE, AGROESTOQUE_PRODUCAO=1
    """
    SECRET_KEY = os.environ.get("AGROESTOQUE_SECRET_KEY", "")
    DATABASE = os.environ.get("AGROESTOQUE_DATABASE", str(RAIZ / "instance" / "agroestoque.sqlite3"))
    TIMEZONE = "America/Fortaleza"
    TOKEN_TTL_SEGUNDOS = 8 * 60 * 60
    MAX_TENTATIVAS_LOGIN = 5
    BLOQUEIO_LOGIN_SEGUNDOS = 15 * 60
    PASSWORD_ITERACOES = 600_000   # PBKDF2-SHA256
    MAX_CONTENT_LENGTH = 1_000_000  # 1 MB por requisição
