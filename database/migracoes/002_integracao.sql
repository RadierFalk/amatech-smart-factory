-- Migração 002: preparação para integrar este banco com os sistemas das outras equipes.

-- Sistemas externos autorizados a usar a API /api/v1 (a chave em si nunca é guardada, só o hash SHA-256).
CREATE TABLE IF NOT EXISTS integracao_clientes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          VARCHAR(50) UNIQUE NOT NULL,          -- ex.: qualidade, manutencao, dashboard
    chave_hash    VARCHAR(64) NOT NULL,
    ativo         INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_por    INTEGER REFERENCES usuarios(id),
    criado_em     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_uso_em TEXT
);

-- Fila de eventos ("outbox"): outros sistemas consultam /api/v1/eventos?apos_id=N para saber o que mudou.
CREATE TABLE IF NOT EXISTS integracao_eventos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo       VARCHAR(50) NOT NULL,                    -- ex.: producao.etapa_alterada
    referencia VARCHAR(100),                            -- ex.: número de série ou SKU
    payload    TEXT NOT NULL,                           -- JSON
    criado_em  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_eventos_tipo ON integracao_eventos(tipo);

-- Não conformidades podem vir de outro sistema (ex.: equipe de Qualidade); id_externo evita duplicidade.
ALTER TABLE nao_conformidades ADD COLUMN origem_sistema VARCHAR(50) NOT NULL DEFAULT 'AMATECH';
ALTER TABLE nao_conformidades ADD COLUMN id_externo VARCHAR(100);
CREATE UNIQUE INDEX IF NOT EXISTS ux_nc_externo ON nao_conformidades(origem_sistema, id_externo)
    WHERE id_externo IS NOT NULL;
