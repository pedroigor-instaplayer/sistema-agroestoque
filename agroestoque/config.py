import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


class Config:
    """Configuração padrão (desenvolvimento). Variáveis de ambiente:

    AGROESTOQUE_SECRET_KEY, AGROESTOQUE_DATABASE, AGROESTOQUE_PRODUCAO=1,
    AGROESTOQUE_GOOGLE_CLIENT_ID (login com Google), ANTHROPIC_API_KEY e
    AGROESTOQUE_MODELO_IA (agente de IA que cadastra produtos por foto)
    """
    SECRET_KEY = os.environ.get("AGROESTOQUE_SECRET_KEY", "")
    DATABASE = os.environ.get("AGROESTOQUE_DATABASE", str(RAIZ / "instance" / "agroestoque.sqlite3"))
    TIMEZONE = "America/Fortaleza"
    TOKEN_TTL_SEGUNDOS = 8 * 60 * 60
    MAX_TENTATIVAS_LOGIN = 5
    BLOQUEIO_LOGIN_SEGUNDOS = 15 * 60
    PASSWORD_ITERACOES = 600_000   # PBKDF2-SHA256
    MAX_CONTENT_LENGTH = 1_000_000  # 1 MB por requisição

    # --- login com Google (Google Identity Services) ---
    GOOGLE_CLIENT_ID = os.environ.get("AGROESTOQUE_GOOGLE_CLIENT_ID", "")

    # --- agente de IA (cadastro de produto por foto) ---
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    MODELO_IA = os.environ.get("AGROESTOQUE_MODELO_IA", "claude-sonnet-5-5")
    AGENTE_MAX_FOTO_BYTES = 6_000_000
    AGENTE_FOTOS_POR_MINUTO = 10
    AGENTE_TIMEOUT_SEGUNDOS = 45
