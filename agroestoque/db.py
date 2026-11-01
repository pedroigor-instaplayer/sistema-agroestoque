"""Acesso ao SQLite (biblioteca padrão), uma conexão por requisição."""
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

SCHEMA = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
MARCADOR_TRIGGERS = "-- @@TRIGGERS@@"


def sem_acento(texto):
    """Normaliza para busca: minúsculas e sem acentos (ex.: 'Ração' -> 'racao')."""
    if texto is None:
        return None
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def conectar(caminho):
    conn = sqlite3.connect(caminho, timeout=10, isolation_level=None)  # autocommit; BEGIN explícito
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.create_function("sem_acento", 1, sem_acento, deterministic=True)
    return conn


def get_db():
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def close_db(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db):
    db.executescript(SCHEMA.read_text(encoding="utf-8"))


def banco_inicializado(db):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='produto'").fetchone() is not None


@contextmanager
def transacao(db):
    """Transação atômica. BEGIN IMMEDIATE serializa escritores (evita saldo inconsistente)."""
    if db.in_transaction:  # já dentro de uma transação externa
        yield db
        return
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
    except BaseException:
        db.execute("ROLLBACK")
        raise
    else:
        db.execute("COMMIT")


def _comandos_triggers():
    """Instruções CREATE TRIGGER do schema.sql (trecho após o marcador)."""
    trecho = SCHEMA.read_text(encoding="utf-8").split(MARCADOR_TRIGGERS, 1)[1].split("\n", 1)[1]
    return [p.strip() + " END" for p in trecho.split("END;") if p.strip()]


@contextmanager
def triggers_suspensos(db):
    """Suspende os triggers de imutabilidade (somente para cargas/limpezas administrativas).

    Não usa executescript (que faria COMMIT implícito), para funcionar dentro de transações.
    """
    db.execute("DROP TRIGGER IF EXISTS trg_mov_sem_update")
    db.execute("DROP TRIGGER IF EXISTS trg_mov_sem_delete")
    try:
        yield db
    finally:
        for comando in _comandos_triggers():
            db.execute(comando)
