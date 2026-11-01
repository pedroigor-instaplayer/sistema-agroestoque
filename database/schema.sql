-- =====================================================================
-- AgroEstoque - Script de criação do banco de dados (SQLite 3)
-- Executado automaticamente por:  flask --app agroestoque init-db
-- ou manualmente:                 sqlite3 instance/agroestoque.sqlite3 < database/schema.sql
--
-- Convenções: datas em UTC no formato 'YYYY-MM-DD HH:MM:SS'; valores
-- monetários em CENTAVOS (INTEGER) para evitar erros de arredondamento.
-- =====================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuario (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT    NOT NULL,
    email      TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash TEXT    NOT NULL,
    papel      TEXT    NOT NULL DEFAULT 'OPERADOR'
                       CHECK (papel IN ('ADMINISTRADOR','GESTOR','OPERADOR')),
    ativo      INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    criado_em  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categoria (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS fornecedor (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    nome               TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    telefone           TEXT    NOT NULL DEFAULT '',
    email              TEXT    NOT NULL DEFAULT '',
    prazo_entrega_dias INTEGER NOT NULL DEFAULT 7 CHECK (prazo_entrega_dias >= 1),
    ativo              INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1))
);

CREATE TABLE IF NOT EXISTS produto (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    sku                  TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    nome                 TEXT    NOT NULL,
    categoria_id         INTEGER NOT NULL REFERENCES categoria (id) ON DELETE RESTRICT,
    unidade              TEXT    NOT NULL DEFAULT 'unidade',
    preco_venda_centavos INTEGER NOT NULL CHECK (preco_venda_centavos >= 0),
    quantidade_atual     INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_atual >= 0),
    estoque_minimo       INTEGER NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
    fornecedor_id        INTEGER NULL REFERENCES fornecedor (id) ON DELETE SET NULL,
    ativo                INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
    criado_em            TEXT    NOT NULL DEFAULT (datetime('now')),
    atualizado_em        TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_produto_nome      ON produto (nome);
CREATE INDEX IF NOT EXISTS idx_produto_categoria ON produto (categoria_id);

CREATE TABLE IF NOT EXISTS movimentacao (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id              INTEGER NOT NULL REFERENCES produto (id) ON DELETE RESTRICT,
    tipo                    TEXT    NOT NULL CHECK (tipo IN ('ENTRADA','SAIDA')),
    motivo                  TEXT    NOT NULL,
    quantidade              INTEGER NOT NULL CHECK (quantidade >= 1),
    valor_unitario_centavos INTEGER NULL CHECK (valor_unitario_centavos IS NULL OR valor_unitario_centavos >= 0),
    saldo_apos              INTEGER NOT NULL CHECK (saldo_apos >= 0),
    observacao              TEXT    NOT NULL DEFAULT '',
    usuario_id              INTEGER NULL REFERENCES usuario (id) ON DELETE SET NULL,
    data                    TEXT    NOT NULL DEFAULT (datetime('now')),
    -- regra de negócio no banco: o motivo precisa ser compatível com o tipo
    CHECK ( (tipo = 'ENTRADA' AND motivo IN ('COMPRA','DEVOLUCAO_CLIENTE','AJUSTE_POSITIVO','ESTOQUE_INICIAL'))
         OR (tipo = 'SAIDA'   AND motivo IN ('VENDA','PERDA','AJUSTE_NEGATIVO','DEVOLUCAO_FORNECEDOR')) )
);
CREATE INDEX IF NOT EXISTS idx_mov_produto_data     ON movimentacao (produto_id, data);
CREATE INDEX IF NOT EXISTS idx_mov_tipo_motivo_data ON movimentacao (tipo, motivo, data);

CREATE TABLE IF NOT EXISTS recomendacao (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id           INTEGER NOT NULL REFERENCES produto (id) ON DELETE CASCADE,
    nivel                TEXT    NOT NULL CHECK (nivel IN ('CRITICO','ATENCAO')),
    status               TEXT    NOT NULL DEFAULT 'PENDENTE'
                                 CHECK (status IN ('PENDENTE','ACEITA','IGNORADA','EXPIRADA')),
    quantidade_sugerida  INTEGER NOT NULL DEFAULT 0,
    saldo_no_calculo     INTEGER NOT NULL DEFAULT 0,
    media_diaria         REAL    NOT NULL DEFAULT 0,
    dias_cobertura       REAL    NULL,
    tendencia_percentual REAL    NULL,
    acao_sugerida        TEXT    NOT NULL DEFAULT '',
    justificativa        TEXT    NOT NULL DEFAULT '',
    gerada_em            TEXT    NOT NULL DEFAULT (datetime('now')),
    decidida_em          TEXT    NULL,
    decidida_por_id      INTEGER NULL REFERENCES usuario (id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_rec_status_nivel ON recomendacao (status, nivel);
CREATE INDEX IF NOT EXISTS idx_rec_produto      ON recomendacao (produto_id);

-- @@TRIGGERS@@  (o trecho abaixo reforça a imutabilidade do livro de estoque)
CREATE TRIGGER IF NOT EXISTS trg_mov_sem_update BEFORE UPDATE ON movimentacao
BEGIN SELECT RAISE(ABORT, 'Movimentações são imutáveis'); END;
CREATE TRIGGER IF NOT EXISTS trg_mov_sem_delete BEFORE DELETE ON movimentacao
BEGIN SELECT RAISE(ABORT, 'Movimentações não podem ser excluídas'); END;
