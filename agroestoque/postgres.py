"""Camada de compatibilidade para consultas SQLite do AgroEstoque no PostgreSQL."""
import re
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None

SCHEMA_PG = Path(__file__).resolve().parent.parent / 'database' / 'schema_postgres.sql'

class Linha(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

class Resultado:
    def __init__(self, cursor, lastrowid=None):
        self.cursor = cursor
        self.lastrowid = lastrowid
    def fetchone(self):
        r = self.cursor.fetchone()
        return Linha(r) if r is not None else None
    def fetchall(self):
        return [Linha(r) for r in self.cursor.fetchall()]
    def __iter__(self):
        return (Linha(r) for r in self.cursor)

class Conexao:
    def __init__(self, url):
        if psycopg is None:
            raise RuntimeError('Instale psycopg[binary] para usar PostgreSQL')
        self.conn = psycopg.connect(url, autocommit=True, row_factory=dict_row)
        self.in_transaction = False
    def execute(self, sql, params=()):
        # O SQL da aplicação usa parâmetros ? do SQLite.
        sql = sql.replace('?', '%s')
        sql = re.sub(r'\bCOLLATE\s+NOCASE\b', '', sql, flags=re.I)
        # INSERTs do aplicativo dependem de cursor.lastrowid.
        insere = bool(re.match(r'^\s*INSERT\s+INTO\s+', sql, flags=re.I))
        if insere and 'RETURNING' not in sql.upper():
            sql = sql.rstrip().rstrip(';') + ' RETURNING id'
        cur = self.conn.execute(sql, params)
        lastid = cur.fetchone()['id'] if insere else None
        return Resultado(cur, lastid)
    def executemany(self, sql, params):
        sql = sql.replace('?', '%s')
        return self.conn.executemany(sql, params)
    def close(self):
        self.conn.close()
    def executescript(self, sql):
        self.conn.execute(sql)

def inicializar(conn):
    # Só inicializa banco novo. Não executar em um banco já populado.
    conn.conn.execute(SCHEMA_PG.read_text(encoding='utf-8'))
