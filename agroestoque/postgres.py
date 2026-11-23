
"""Compatibilidade entre consultas SQLite e PostgreSQL do AgroEstoque."""

import re
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

SCHEMA_PG = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "schema_postgres.sql"
)


class Linha(dict):
    """Permite acessar resultados por nome ou posição."""

    def __getitem__(self, key):
        if isinstance(key, int):
            valores = list(self.values())
            return valores[key]
        return super().__getitem__(key)


class Resultado:
    def __init__(self, cursor, lastrowid=None, primeira_linha=None):
        self.cursor = cursor
        self.lastrowid = lastrowid
        self.primeira_linha = primeira_linha

    def fetchone(self):
        if self.primeira_linha is not None:
            linha = self.primeira_linha
            self.primeira_linha = None
            return Linha(linha)

        resultado = self.cursor.fetchone()
        return Linha(resultado) if resultado is not None else None

    def fetchall(self):
        linhas = []

        if self.primeira_linha is not None:
            linhas.append(Linha(self.primeira_linha))
            self.primeira_linha = None

        linhas.extend(Linha(r) for r in self.cursor.fetchall())
        return linhas

    def __iter__(self):
        while True:
            linha = self.fetchone()
            if linha is None:
                break
            yield linha


class Conexao:
    def __init__(self, url):
        self.conn = psycopg.connect(
            url,
            autocommit=True,
            row_factory=dict_row,
        )
        self.in_transaction = False

    def execute(self, sql, params=()):
        sql = re.sub(
            r"\bCOLLATE\s+NOCASE\b",
            "",
            sql,
            flags=re.IGNORECASE,
        )

        sql = sql.replace("?", "%s")

        insere = bool(
            re.match(
                r"^\s*INSERT\s+INTO\s+",
                sql,
                flags=re.IGNORECASE,
            )
        )

        returning_original = bool(
            re.search(r"\bRETURNING\b", sql, flags=re.IGNORECASE)
        )

        if insere and not returning_original:
            sql = sql.rstrip().rstrip(";") + " RETURNING id"

        cursor = self.conn.execute(sql, params)

        lastrowid = None
        primeira_linha = None

        if insere:
            primeira_linha = cursor.fetchone()
            if primeira_linha is not None:
                lastrowid = primeira_linha.get("id")

        return Resultado(
            cursor,
            lastrowid=lastrowid,
            primeira_linha=primeira_linha,
        )

    def executemany(self, sql, params):
        sql = sql.replace("?", "%s")
        return self.conn.executemany(sql, params)

    def close(self):
        self.conn.close()

    def executescript(self, sql):
        self.conn.execute(sql)


def inicializar(conn):
    """Inicializa a estrutura PostgreSQL quando necessário."""
    conn.conn.execute(SCHEMA_PG.read_text(encoding="utf-8"))

