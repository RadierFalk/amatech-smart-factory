-- =====================================================================
-- AMATECH Electronics - Sistema de Rastreabilidade de Produtos (SQLite)
-- Migração 001 = script original da equipe, com 2 ajustes marcados como "AJUSTE":
--   1) usuarios.matricula        -> a tela de login usa matrícula (ex.: MAT-00421)
--   2) status_producao.ordem     -> define a sequência das etapas ("avançar etapa")
-- ATENÇÃO: o SQLite precisa do PRAGMA foreign_keys = ON em CADA conexão
-- (o app já faz isso em app/db.py); sem ele as chaves estrangeiras são ignoradas.
-- =====================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    matricula     VARCHAR(20) UNIQUE NOT NULL,          -- AJUSTE
    nome          VARCHAR(100) NOT NULL,
    email         VARCHAR(100) UNIQUE NOT NULL,
    senha_hash    VARCHAR(255) NOT NULL,
    cargo         VARCHAR(50)  NOT NULL,
    ativo         INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_por    INTEGER REFERENCES usuarios(id),
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS status_producao (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_status   VARCHAR(50) UNIQUE NOT NULL,
    ordem         INTEGER NOT NULL DEFAULT 0,           -- AJUSTE
    criado_por    INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS produtos (
    idprd         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_modelo   VARCHAR(100) NOT NULL,
    codigo_modelo VARCHAR(50) UNIQUE NOT NULL,
    quantidade    INTEGER,
    criado_por    INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS componentes (
    idcmp         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          VARCHAR(100) NOT NULL,
    codigo_sku    VARCHAR(50) UNIQUE NOT NULL,
    qtd_estoque   INTEGER DEFAULT 0,
    criado_por    INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS produto_componentes (
    produto_id            INTEGER REFERENCES produtos(idprd),
    componente_id         INTEGER REFERENCES componentes(idcmp),
    quantidade_necessaria INTEGER NOT NULL,
    criado_por            INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (produto_id, componente_id)
);

CREATE TABLE IF NOT EXISTS producoes (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_serie_notebook   VARCHAR(100) UNIQUE NOT NULL,
    id_unica_producao       VARCHAR(100) UNIQUE NOT NULL,
    produto_id              INTEGER REFERENCES produtos(idprd),
    status_atual_id         INTEGER REFERENCES status_producao(id),
    data_inicio             TEXT DEFAULT CURRENT_TIMESTAMP,
    responsavel_etapa_id    INTEGER REFERENCES usuarios(id),
    criado_por              INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em               TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historico_passagem (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    producao_id             INTEGER REFERENCES producoes(id),
    status_id               INTEGER REFERENCES status_producao(id),
    usuario_id              INTEGER NOT NULL REFERENCES usuarios(id),
    responsavel_etapa_id    INTEGER REFERENCES usuarios(id),
    data_horario            TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    origem_atualizacao      VARCHAR(50) DEFAULT 'MANUAL' -- MANUAL ou MAQUINA/IOT
);

CREATE TABLE IF NOT EXISTS nao_conformidades (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    producao_id       INTEGER REFERENCES producoes(id),
    usuario_id        INTEGER NOT NULL REFERENCES usuarios(id),
    descricao_falha   TEXT NOT NULL,
    motivo_reprovacao TEXT NOT NULL,
    data_registro     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS solicitacoes_materiais (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    producao_id            INTEGER REFERENCES producoes(id),
    componente_id          INTEGER REFERENCES componentes(idcmp),
    quantidade_solicitada  INTEGER NOT NULL,
    status_solicitacao     VARCHAR(30) DEFAULT 'PENDENTE',  -- PENDENTE, PARCIAL, ATENDIDA, CANCELADA
    criado_por             INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS baixas_materiais (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitacao_id      INTEGER REFERENCES solicitacoes_materiais(id),
    usuario_id          INTEGER NOT NULL REFERENCES usuarios(id),
    quantidade_baixada  INTEGER NOT NULL,
    data_baixa          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Índices (acesso rápido ao histórico e às solicitações de cada produção)
CREATE INDEX IF NOT EXISTS idx_producoes_status      ON producoes(status_atual_id);
CREATE INDEX IF NOT EXISTS idx_historico_producao    ON historico_passagem(producao_id);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_producao ON solicitacoes_materiais(producao_id);
CREATE INDEX IF NOT EXISTS idx_baixas_solicitacao    ON baixas_materiais(solicitacao_id);
