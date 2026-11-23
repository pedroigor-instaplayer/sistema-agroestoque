"""Acesso ao SQLite (biblioteca padrão), uma conexão por requisição."""
import sqlite3
import unicodedata
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g
import os

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
        url = current_app.config.get("DATABASE_URL")
        if url:
            from .postgres import Conexao
            g.db = Conexao(url)
        else:
            g.db = conectar(current_app.config["DATABASE"])
    return g.db


def close_db(_erro=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db):
    if hasattr(db, "conn"):
        from .postgres import inicializar
        return inicializar(db)
    db.executescript(SCHEMA.read_text(encoding="utf-8"))


def banco_inicializado(db):
    if hasattr(db, "conn"):
        return db.execute("SELECT 1 FROM information_schema.tables WHERE table_schema = current_schema() AND table_name = 'produto'").fetchone() is not None
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='produto'").fetchone() is not None


@contextmanager
def transacao(db):
    """Transação atômica. BEGIN IMMEDIATE serializa escritores (evita saldo inconsistente)."""
    if db.in_transaction:  # já dentro de uma transação externa
        yield db
        return
    db.execute("BEGIN" if hasattr(db, "conn") else "BEGIN IMMEDIATE")
    if hasattr(db, "conn"):
        db.in_transaction = True
    try:
        yield db
    except BaseException:
        db.execute("ROLLBACK")
        raise
    else:
        db.execute("COMMIT")
    finally:
        if hasattr(db, "conn"):
            db.in_transaction = False


def _comandos_triggers():
    """Instruções CREATE TRIGGER do schema.sql (trecho após o marcador)."""
    trecho = SCHEMA.read_text(encoding="utf-8").split(MARCADOR_TRIGGERS, 1)[1].split("\n", 1)[1]
    return [p.strip() + " END" for p in trecho.split("END;") if p.strip()]


@contextmanager
def triggers_suspensos(db):
    """Suspende os triggers de imutabilidade (somente para cargas/limpezas administrativas).

    Não usa executescript (que faria COMMIT implícito), para funcionar dentro de transações.
    """
    if hasattr(db, "conn"):
        db.execute("DROP TRIGGER IF EXISTS trg_mov_sem_update ON movimentacao")
        db.execute("DROP TRIGGER IF EXISTS trg_mov_sem_delete ON movimentacao")
        try:
            yield db
        finally:
            db.execute("CREATE TRIGGER trg_mov_sem_update BEFORE UPDATE ON movimentacao FOR EACH ROW EXECUTE FUNCTION impedir_movimentacao()")
            db.execute("CREATE TRIGGER trg_mov_sem_delete BEFORE DELETE ON movimentacao FOR EACH ROW EXECUTE FUNCTION impedir_movimentacao()")
        return
    db.execute("DROP TRIGGER IF EXISTS trg_mov_sem_update")
    db.execute("DROP TRIGGER IF EXISTS trg_mov_sem_delete")
    try:
        yield db
    finally:
        for comando in _comandos_triggers():
            db.execute(comando)
