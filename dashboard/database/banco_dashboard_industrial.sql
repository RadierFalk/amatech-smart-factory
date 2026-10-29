-- =====================================================================
-- AMATECH Smart Factory — Projeto 3: Dashboard Industrial
-- Problema 8: Indicadores dispersos
-- Script de criação do banco de dados (SQLite) — versão final da OA2
-- Equipe: Letícia, Vinicius, Mateus, Radier, Jose Orlando
--
-- Como usar:  sqlite3 banco.db < banco_dashboard_industrial.sql
-- Observação: os indicadores NÃO são armazenados no banco. Eles são
-- calculados na consulta pela classe CalculadoraIndicadores (camada 2, Python),
-- decisão da OA2. O banco guarda apenas dados brutos e garante as regras de integridade.
--
-- OA3 (integração com os outros setores): registro_producao, defeito, retrabalho e parada
-- ganharam origem_sistema e id_externo. Quando o dado vem da sincronização com outro sistema
-- (Rastreabilidade, Qualidade ou Manutenção), o par (origem_sistema, id_externo) identifica o
-- registro de lá; sincronizar de novo atualiza o registro em vez de duplicar.
-- O app.py cria o banco automaticamente a partir deste script na primeira execução.
-- =====================================================================

PRAGMA foreign_keys = ON;   -- obrigatório no SQLite para validar as FKs (RNF04)

-- =====================================================================
-- 1. ACESSO (RF18, RF19, RNF07)
-- =====================================================================
CREATE TABLE perfil (
    id_perfil   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL UNIQUE,
    descricao   TEXT
);

CREATE TABLE usuario (
    id_usuario  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome        TEXT    NOT NULL,
    login       TEXT    NOT NULL UNIQUE,
    senha_hash  TEXT    NOT NULL,                         -- nunca a senha em texto (RNF07)
    id_perfil   INTEGER NOT NULL REFERENCES perfil(id_perfil),
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    criado_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- =====================================================================
-- 2. CADASTROS BÁSICOS
-- =====================================================================
CREATE TABLE turno (
    id_turno     INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT    NOT NULL UNIQUE,
    hora_inicio  TEXT    NOT NULL,                        -- 'HH:MM'
    hora_fim     TEXT    NOT NULL,
    duracao_min  INTEGER NOT NULL CHECK (duracao_min > 0) -- usado na produtividade
);

CREATE TABLE produto (
    id_produto  INTEGER PRIMARY KEY AUTOINCREMENT,
    modelo      TEXT    NOT NULL UNIQUE,
    descricao   TEXT,
    ativo       INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
);

CREATE TABLE estacao (
    id_estacao   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         TEXT    NOT NULL UNIQUE,
    setor        TEXT,
    ordem_fluxo  INTEGER                                   -- posição no fluxo produtivo
);

CREATE TABLE maquina (
    id_maquina  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT    NOT NULL UNIQUE,
    nome        TEXT    NOT NULL,
    id_estacao  INTEGER NOT NULL REFERENCES estacao(id_estacao)
);

CREATE TABLE tipo_defeito (
    id_tipo_defeito  INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao        TEXT    NOT NULL UNIQUE,
    categoria        TEXT                                  -- ex.: funcional, visual, documental
);

CREATE TABLE motivo_parada (
    id_motivo  INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao  TEXT    NOT NULL UNIQUE,
    tipo       TEXT    NOT NULL CHECK (tipo IN ('corretiva', 'preventiva', 'operacional'))
);

CREATE TABLE tipo_perda (
    id_tipo_perda  INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao      TEXT    NOT NULL UNIQUE
);

-- Limites configuráveis do semáforo (RF17, RN08); ajustados pelo Supervisor (UC16)
CREATE TABLE parametro_alerta (
    id_parametro    INTEGER PRIMARY KEY AUTOINCREMENT,
    indicador       TEXT    NOT NULL UNIQUE,
    limite_verde    REAL    NOT NULL,
    limite_amarelo  REAL    NOT NULL,
    sentido         TEXT    NOT NULL CHECK (sentido IN ('maior_melhor', 'menor_melhor'))
);

-- =====================================================================
-- 3. IMPORTAÇÃO DE PLANILHAS (RF16, RN06)
-- =====================================================================
CREATE TABLE importacao (
    id_importacao      INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_arquivo       TEXT    NOT NULL,
    tipo_dado          TEXT    NOT NULL CHECK (tipo_dado IN ('producao', 'defeito', 'parada', 'perda')),
    data_hora          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    id_usuario         INTEGER NOT NULL REFERENCES usuario(id_usuario),
    linhas_lidas       INTEGER NOT NULL DEFAULT 0 CHECK (linhas_lidas >= 0),
    linhas_importadas  INTEGER NOT NULL DEFAULT 0 CHECK (linhas_importadas >= 0),
    linhas_rejeitadas  INTEGER NOT NULL DEFAULT 0 CHECK (linhas_rejeitadas >= 0),
    status             TEXT    NOT NULL CHECK (status IN ('concluida', 'rejeitada'))
);

-- =====================================================================
-- 4. REGISTROS DE EVENTOS DA LINHA
-- =====================================================================
-- Meta por data + turno + produto (RF02, RN03, RN09)
CREATE TABLE meta_producao (
    id_meta         INTEGER PRIMARY KEY AUTOINCREMENT,
    data            TEXT    NOT NULL,                      -- 'AAAA-MM-DD'
    id_turno        INTEGER NOT NULL REFERENCES turno(id_turno),
    id_produto      INTEGER NOT NULL REFERENCES produto(id_produto),
    qtd_meta        INTEGER NOT NULL CHECK (qtd_meta > 0),
    registrado_por  INTEGER NOT NULL REFERENCES usuario(id_usuario),
    UNIQUE (data, id_turno, id_produto)                    -- RN09
);

-- Produção realizada (RF01, RN01)
CREATE TABLE registro_producao (
    id_producao     INTEGER PRIMARY KEY AUTOINCREMENT,
    data            TEXT    NOT NULL,                      -- RN01
    id_turno        INTEGER NOT NULL REFERENCES turno(id_turno),     -- RN01
    id_produto      INTEGER NOT NULL REFERENCES produto(id_produto), -- RN01
    qtd_realizada   INTEGER NOT NULL CHECK (qtd_realizada >= 0),
    qtd_aprovada    INTEGER NOT NULL CHECK (qtd_aprovada >= 0),
    qtd_reprovada   INTEGER NOT NULL CHECK (qtd_reprovada >= 0),
    registrado_por  INTEGER NOT NULL REFERENCES usuario(id_usuario),
    registrado_em   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    id_importacao   INTEGER REFERENCES importacao(id_importacao),    -- NULL = lançado no formulário
    origem_sistema  TEXT,                                            -- NULL = lançado no Dashboard
    id_externo      TEXT,                                            -- id do registro no sistema de origem
    CHECK (qtd_aprovada + qtd_reprovada = qtd_realizada)             -- RNF04
);

-- Defeitos por estação (RF03)
CREATE TABLE defeito (
    id_defeito       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producao      INTEGER NOT NULL REFERENCES registro_producao(id_producao),
    id_tipo_defeito  INTEGER NOT NULL REFERENCES tipo_defeito(id_tipo_defeito),
    id_estacao       INTEGER NOT NULL REFERENCES estacao(id_estacao),
    id_maquina       INTEGER REFERENCES maquina(id_maquina),         -- opcional (OA1, 9.1)
    quantidade       INTEGER NOT NULL CHECK (quantidade > 0),
    data_hora        TEXT    NOT NULL,
    observacao       TEXT,
    registrado_por   INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_importacao    INTEGER REFERENCES importacao(id_importacao),
    origem_sistema   TEXT,
    id_externo       TEXT
);

-- Retrabalho com etapa de retorno (RF04, RN02)
CREATE TABLE retrabalho (
    id_retrabalho       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_defeito          INTEGER NOT NULL REFERENCES defeito(id_defeito),
    id_estacao_retorno  INTEGER NOT NULL REFERENCES estacao(id_estacao),
    motivo              TEXT    NOT NULL,
    quantidade          INTEGER NOT NULL CHECK (quantidade > 0),
    data_hora           TEXT    NOT NULL,
    registrado_por      INTEGER NOT NULL REFERENCES usuario(id_usuario),
    origem_sistema      TEXT,
    id_externo          TEXT
);

-- Paradas de linha (RF05, RN04). fim NULL = parada ainda em andamento.
CREATE TABLE parada (
    id_parada       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_estacao      INTEGER NOT NULL REFERENCES estacao(id_estacao),
    id_maquina      INTEGER REFERENCES maquina(id_maquina),
    id_turno        INTEGER NOT NULL REFERENCES turno(id_turno),
    id_motivo       INTEGER NOT NULL REFERENCES motivo_parada(id_motivo), -- RN04
    inicio          TEXT    NOT NULL,                      -- 'AAAA-MM-DD HH:MM'
    fim             TEXT,
    observacao      TEXT,
    registrado_por  INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_importacao   INTEGER REFERENCES importacao(id_importacao),
    origem_sistema  TEXT,
    id_externo      TEXT,
    CHECK (fim IS NULL OR fim > inicio)
);

-- Perdas (RF15, RN07)
CREATE TABLE perda (
    id_perda        INTEGER PRIMARY KEY AUTOINCREMENT,
    data            TEXT    NOT NULL,
    id_turno        INTEGER NOT NULL REFERENCES turno(id_turno),
    id_estacao      INTEGER NOT NULL REFERENCES estacao(id_estacao),
    id_produto      INTEGER NOT NULL REFERENCES produto(id_produto),
    id_tipo_perda   INTEGER NOT NULL REFERENCES tipo_perda(id_tipo_perda), -- RN07
    quantidade      INTEGER NOT NULL CHECK (quantidade > 0),               -- RN07
    observacao      TEXT,
    registrado_por  INTEGER NOT NULL REFERENCES usuario(id_usuario),
    id_importacao   INTEGER REFERENCES importacao(id_importacao)
);

-- Índices para as consultas filtradas do painel (RNF02, RF12)
CREATE INDEX idx_producao_filtro ON registro_producao (data, id_turno, id_produto);
CREATE INDEX idx_meta_filtro     ON meta_producao     (data, id_turno, id_produto);
CREATE INDEX idx_parada_inicio   ON parada            (inicio, id_turno);
CREATE INDEX idx_perda_filtro    ON perda             (data, id_turno, id_produto);
CREATE INDEX idx_defeito_prod    ON defeito           (id_producao);

-- Um mesmo registro de outro sistema entra uma única vez (sincronização sem duplicar)
CREATE UNIQUE INDEX ux_producao_externo   ON registro_producao (origem_sistema, id_externo) WHERE id_externo IS NOT NULL;
CREATE UNIQUE INDEX ux_defeito_externo    ON defeito           (origem_sistema, id_externo) WHERE id_externo IS NOT NULL;
CREATE UNIQUE INDEX ux_retrabalho_externo ON retrabalho        (origem_sistema, id_externo) WHERE id_externo IS NOT NULL;
CREATE UNIQUE INDEX ux_parada_externo     ON parada            (origem_sistema, id_externo) WHERE id_externo IS NOT NULL;

-- =====================================================================
-- 5. DADOS INICIAIS E DADOS SIMULADOS (baseados no item 2.8 do enunciado)
-- =====================================================================
INSERT INTO perfil (nome, descricao) VALUES
 ('Operador de estação',    'Registra produção e defeitos'),
 ('Inspetor de qualidade',  'Registra defeitos e retrabalho'),
 ('Manutenção',             'Registra paradas'),
 ('Supervisor de produção', 'Registros, metas, perdas, importação, painel, histórico e limites do semáforo'),
 ('Gestor/Diretoria',       'Painel, filtros e histórico (somente leitura)'),
 ('Administrador',          'Usuários, perfis e cadastros básicos');

-- Usuários de teste, um por perfil (somente para testes; trocar as senhas antes de qualquer uso real).
-- Senhas protegidas com PBKDF2-SHA256 + sal (hashlib), formato "pbkdf2_sha256$iterações$sal$hash" (RNF07).
-- admin/admin123 · supervisor/super123 · gestor/gestor123 · operador/oper123 · inspetor/insp123 · manutencao/manut123
INSERT INTO usuario (nome, login, senha_hash, id_perfil) VALUES
 ('Administrador do sistema', 'admin',
  'pbkdf2_sha256$200000$2a749bbfdb6975587c0f333750989db5$aed48177dd4d2dbf76b9943f49c45f22e730b99efd116dadcbd2ba76c52707c4', 6),
 ('Maria Souza', 'supervisor',
  'pbkdf2_sha256$200000$7c71c22036294a5a62eb7fd7addc2bd1$c3bb8911e9ae9225489b599253964eebf5cd807b11687d63ffb74f5414a27776', 4),
 ('Paulo Andrade', 'gestor',
  'pbkdf2_sha256$200000$c2454efbedfafc31fd69144c64bea1c6$bf0f862471b1066bed2cbef83d91c81e18955582cb41bf9b04c09435eac8fc28', 5),
 ('João Pereira', 'operador',
  'pbkdf2_sha256$200000$56068f268441fc81c44dd0f6f9a50d18$de9fd4374339550cd207b528fb0280cd8f443791d1f7fc687dff7661e484f1c1', 1),
 ('Rita Campos', 'inspetor',
  'pbkdf2_sha256$200000$f0fa8f9521aabdcc5e18d94960daf0f3$620edcca36e5daa61d5e6c82a11e75164de0401d34af4f2988445f24fb3700ce', 2),
 ('Sérgio Melo', 'manutencao',
  'pbkdf2_sha256$200000$ad2d3f0582ee1c3a9fb631bc81a59586$296841b9849bd60498887cd36c26b7eaff9af85025474e213ab282b05068d792', 3);

INSERT INTO turno (nome, hora_inicio, hora_fim, duracao_min) VALUES
 ('1º turno', '06:00', '14:00', 480),
 ('2º turno', '14:00', '22:00', 480);

INSERT INTO produto (modelo, descricao) VALUES
 ('Notebook modelo A', 'Configuração de referência (dados simulados)'),
 ('Notebook modelo B', 'Configuração alternativa (dados simulados)');

INSERT INTO estacao (nome, setor, ordem_fluxo) VALUES
 ('Linha SMT',              'Produção', 1),
 ('Inserção manual',        'Produção', 2),
 ('Montagem final',         'Produção', 3),
 ('Instalação de software', 'Produção', 4),
 ('Teste funcional',        'Qualidade', 5),
 ('Inspeção da qualidade',  'Qualidade', 6),
 ('Embalagem',              'Expedição', 7);

INSERT INTO maquina (codigo, nome, id_estacao) VALUES
 ('TST-02', 'Testador 02', 5);

INSERT INTO tipo_defeito (descricao, categoria) VALUES
 ('Falha no teclado',   'funcional'),
 ('Falha no touchpad',  'funcional'),
 ('Tela com defeito',   'visual'),
 ('Etiqueta incorreta', 'documental'),
 -- Lista comum com o Controle da Qualidade (cadastros comuns do ecossistema, OA3)
 ('Falha de USB',             'funcional'),
 ('Falha de áudio',           'funcional'),
 ('Falha no Wi-Fi',           'funcional'),
 ('Falha na câmera',          'funcional'),
 ('Falha na bateria',         'funcional'),
 ('Falha no armazenamento',   'funcional'),
 ('Desempenho insuficiente',  'funcional'),
 ('Falha de montagem',        'visual'),
 ('Falha de software',        'funcional');

INSERT INTO motivo_parada (descricao, tipo) VALUES
 ('Falha de equipamento',  'corretiva'),
 ('Manutenção programada', 'preventiva'),
 ('Falta de material',     'operacional');

INSERT INTO tipo_perda (descricao) VALUES
 ('Componente danificado'), ('Material descartado'), ('Embalagem danificada');

INSERT INTO parametro_alerta (indicador, limite_verde, limite_amarelo, sentido) VALUES
 ('atendimento_meta', 95, 75, 'maior_melhor'),
 ('indice_defeitos',   2,  5, 'menor_melhor'),
 ('indice_retrabalho', 2,  5, 'menor_melhor');

-- Exemplo do enunciado: 15/08/2026, 1º turno, modelo A, meta 1.500,
-- 1.420 produzidos, 1.360 aprovados, 60 reprovados, 85 min de parada no Testador 02.
INSERT INTO meta_producao (data, id_turno, id_produto, qtd_meta, registrado_por) VALUES
 ('2026-08-15', 1, 1, 1500, 1);

INSERT INTO registro_producao (data, id_turno, id_produto, qtd_realizada, qtd_aprovada, qtd_reprovada, registrado_por) VALUES
 ('2026-08-15', 1, 1, 1420, 1360, 60, 1);

INSERT INTO defeito (id_producao, id_tipo_defeito, id_estacao, id_maquina, quantidade, data_hora, registrado_por) VALUES
 (1, 1, 5, 1, 45, '2026-08-15 09:30', 1),
 (1, 3, 6, NULL, 15, '2026-08-15 11:10', 1);

INSERT INTO retrabalho (id_defeito, id_estacao_retorno, motivo, quantidade, data_hora, registrado_por) VALUES
 (1, 3, 'Substituição do teclado', 30, '2026-08-15 10:00', 1);

INSERT INTO parada (id_estacao, id_maquina, id_turno, id_motivo, inicio, fim, registrado_por) VALUES
 (5, 1, 1, 1, '2026-08-15 08:00', '2026-08-15 09:25', 1);

INSERT INTO perda (data, id_turno, id_estacao, id_produto, id_tipo_perda, quantidade, registrado_por) VALUES
 ('2026-08-15', 1, 3, 1, 1, 8, 1);
