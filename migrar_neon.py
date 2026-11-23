
"""Migração única do SQLite local para Neon. Não modifica o SQLite."""
import getpass
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

try:
    import psycopg
except ImportError:
    raise SystemExit('Instale: python -m pip install "psycopg[binary]>=3.2,<4"')

ROOT = Path(__file__).resolve().parent
ORIGEM = ROOT / 'instance' / 'agroestoque.sqlite3'
SCHEMA = ROOT / 'database' / 'schema_postgres.sql'
TABELAS = ('usuario', 'categoria', 'fornecedor', 'produto', 'movimentacao', 'recomendacao')

if not ORIGEM.is_file():
    raise SystemExit(f'Banco SQLite não encontrado: {ORIGEM}')

url = getpass.getpass('Cole a Connection string do Neon (não aparece na tela): ').strip()

if not url.startswith(('postgresql://', 'postgres://')):
    raise SystemExit('Conexão inválida; copie somente a URL postgresql://...')

# Remove o parâmetro incompatível, preservando sslmode=require.
partes = urlsplit(url)
parametros = [
    (chave, valor)
    for chave, valor in parse_qsl(partes.query, keep_blank_values=True)
    if chave.lower() != 'channel_binding'
]
url = urlunsplit((
    partes.scheme,
    partes.netloc,
    partes.path,
    urlencode(parametros),
    partes.fragment,
))

src = sqlite3.connect(f'file:{ORIGEM.as_posix()}?mode=ro', uri=True)
src.row_factory = sqlite3.Row

if src.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
    raise SystemExit('Integridade SQLite falhou; migração cancelada.')

contagens = {
    tabela: src.execute(f'SELECT COUNT(*) FROM {tabela}').fetchone()[0]
    for tabela in TABELAS
}

print('Registros no SQLite:', contagens)
print('ATENÇÃO: a migração só aceita Neon vazio. Não apaga tabelas existentes.')

if input('Digite MIGRAR para continuar: ').strip() != 'MIGRAR':
    raise SystemExit('Cancelado.')

try:
    with psycopg.connect(url, autocommit=False) as dst:
        with dst.cursor() as cur:
            # Estrutura e registros na mesma transação.
            cur.execute(SCHEMA.read_text(encoding='utf-8'))

            for tabela in TABELAS:
                cur.execute(f'SELECT COUNT(*) FROM {tabela}')
                if cur.fetchone()[0] != 0:
                    raise RuntimeError(
                        f'{tabela} não está vazia no Neon. Nenhum dado foi alterado.'
                    )

            for tabela in TABELAS:
                dados = src.execute(f'SELECT * FROM {tabela}').fetchall()

                if dados:
                    colunas = list(dados[0].keys())
                    nomes_colunas = ', '.join(colunas)
                    placeholders = ', '.join(['%s'] * len(colunas))

                    comando = (
                        f'INSERT INTO {tabela} ({nomes_colunas}) '
                        f'VALUES ({placeholders})'
                    )

                    cur.executemany(
                        comando,
                        [tuple(registro) for registro in dados]
                    )

                cur.execute(f'SELECT COUNT(*) FROM {tabela}')
                if cur.fetchone()[0] != contagens[tabela]:
                    raise RuntimeError(f'Contagem divergente: {tabela}')

                cur.execute(
                    f"SELECT setval("
                    f"pg_get_serial_sequence('{tabela}', 'id'), "
                    f"GREATEST((SELECT COALESCE(MAX(id), 0) FROM {tabela}), 1), "
                    f"(SELECT COUNT(*) > 0 FROM {tabela}))"
                )

            print(
                'Conferência concluída:',
                sum(contagens.values()),
                'registros.'
            )

        dst.commit()

finally:
    src.close()

print('MIGRAÇÃO CONCLUÍDA. Configure DATABASE_URL no Render.')
