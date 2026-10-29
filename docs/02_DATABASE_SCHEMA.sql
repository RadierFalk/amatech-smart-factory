-- ==============================================================================
-- AMATECH SMART FACTORY - PROJETO 5: SISTEMA DE CONTROLE DA MANUTENÇÃO
-- DDL & SEED DATA - COMPATÍVEL COM SQLITE E POSTGRESQL
-- ==============================================================================

-- 1. TABELA DE USUÁRIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL,
    matricula VARCHAR(20) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    perfil VARCHAR(20) NOT NULL CHECK (perfil IN ('OPERADOR', 'TECNICO', 'GESTOR')),
    ativo BOOLEAN NOT NULL DEFAULT 1,
    criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABELA DE EQUIPAMENTOS / MÁQUINAS
CREATE TABLE IF NOT EXISTS equipamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_tag VARCHAR(30) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    setor VARCHAR(50) NOT NULL,
    posto_trabalho VARCHAR(50),
    status_operacional VARCHAR(20) NOT NULL DEFAULT 'OPERACIONAL' CHECK (status_operacional IN ('OPERACIONAL', 'EM_MANUTENCAO', 'PARADA')),
    ativo BOOLEAN NOT NULL DEFAULT 1
);

-- 3. TABELA DE CHAMADOS DE MANUTENÇÃO (ORDEM DE SERVIÇO)
CREATE TABLE IF NOT EXISTS chamados_manutencao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id),
    operador_abertura_id INTEGER NOT NULL REFERENCES usuarios(id),
    tecnico_responsavel_id INTEGER REFERENCES usuarios(id),
    prioridade VARCHAR(20) NOT NULL CHECK (prioridade IN ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA')),
    tipo_manutencao VARCHAR(20) NOT NULL DEFAULT 'CORRETIVA' CHECK (tipo_manutencao IN ('CORRETIVA', 'PREVENTIVA')),
    status_chamado VARCHAR(20) NOT NULL DEFAULT 'ABERTO' CHECK (status_chamado IN ('ABERTO', 'EM_ANDAMENTO', 'CONCLUIDO', 'CANCELADO')),
    descricao_falha TEXT NOT NULL,
    diagnostico_tecnico TEXT,
    causa_raiz VARCHAR(150),
    data_hora_abertura TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_hora_inicio_atendimento TIMESTAMP,
    data_hora_fim_atendimento TIMESTAMP,
    downtime_minutos INTEGER CHECK (downtime_minutos IS NULL OR downtime_minutos >= 0),
    origem_sistema VARCHAR(50),        -- sistema que abriu o chamado pela API (ex.: qualidade); vazio = tela
    id_externo VARCHAR(100)            -- id do registro no sistema de origem (evita chamado duplicado)
);

-- 4. TABELA DO CATÁLOGO DE PEÇAS / INSUMOS
CREATE TABLE IF NOT EXISTS pecas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_peca VARCHAR(50) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    unidade_medida VARCHAR(10) NOT NULL DEFAULT 'UN',
    ativo BOOLEAN NOT NULL DEFAULT 1
);

-- 5. TABELA ASSOCIATIVA DE PEÇAS SUBSTITUÍDAS NA OS
CREATE TABLE IF NOT EXISTS chamado_pecas_trocadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chamado_id INTEGER NOT NULL REFERENCES chamados_manutencao(id) ON DELETE CASCADE,
    peca_id INTEGER NOT NULL REFERENCES pecas(id),
    quantidade NUMERIC(10,2) NOT NULL CHECK (quantidade > 0)
);

-- 6. TABELA DE HISTÓRICO E AUDITORIA DE STATUS (RNF02 / RN08)
CREATE TABLE IF NOT EXISTS historico_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipamento_id INTEGER NOT NULL REFERENCES equipamentos(id),
    chamado_id INTEGER REFERENCES chamados_manutencao(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    status_anterior VARCHAR(20) NOT NULL CHECK (status_anterior IN ('OPERACIONAL', 'EM_MANUTENCAO', 'PARADA')),
    status_novo VARCHAR(20) NOT NULL CHECK (status_novo IN ('OPERACIONAL', 'EM_MANUTENCAO', 'PARADA')),
    alterado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ÍNDICES DE PERFORMANCE (RNF03 - CONSULTAS < 3 SEGUNDOS)
CREATE INDEX IF NOT EXISTS ix_chamados_status ON chamados_manutencao(status_chamado);
CREATE INDEX IF NOT EXISTS ix_chamados_equip_data ON chamados_manutencao(equipamento_id, data_hora_abertura);
CREATE INDEX IF NOT EXISTS ix_chamados_tecnico ON chamados_manutencao(tecnico_responsavel_id);
CREATE INDEX IF NOT EXISTS ix_hist_equip ON historico_status(equipamento_id, alterado_em);
CREATE UNIQUE INDEX IF NOT EXISTS ux_chamados_externo ON chamados_manutencao(origem_sistema, id_externo)
    WHERE id_externo IS NOT NULL;

-- ==============================================================================
-- CARGA INICIAL DE DADOS (SEED DATA REALISTA DO PARQUE FABRIL AMATECH)
-- ==============================================================================

-- Usuários iniciais (senhas padrão hash SHA-256 ou bcrypt para testes: '123456')
-- Hash SHA-256 de '123456': e10adc3949ba59abbe56e057f20f883e (ou senha texto para simplicidade inicial)
INSERT INTO usuarios (nome, matricula, senha_hash, perfil, ativo) VALUES
('Carlos Mendonça', 'OP-10234', '123456', 'OPERADOR', 1),
('Lucas Ferreira', 'OP-10235', '123456', 'OPERADOR', 1),
('João Lima Silva', 'TEC-2001', '123456', 'TECNICO', 1),
('Mariana Rocha', 'TEC-2002', '123456', 'TECNICO', 1),
('Orlando Vandres', 'GES-0001', '123456', 'GESTOR', 1),
('Dawesley Costa', 'GES-0002', '123456', 'GESTOR', 1),
-- Usuário de serviço (inativo, não faz login): operador de abertura dos chamados que chegam pela API
('Integração (outros sistemas)', 'SVC-INTEGRACAO', '!', 'OPERADOR', 0);

-- Equipamentos compatíveis com os módulos de Controle de Qualidade e Rastreabilidade
INSERT INTO equipamentos (codigo_tag, nome, setor, posto_trabalho, status_operacional, ativo) VALUES
('SMT-01', 'Insersora Automática High-Speed', 'SMT', 'Posto 01', 'OPERACIONAL', 1),
('SMT-02', 'Forno de Refusão 10 Zonas', 'SMT', 'Posto 02', 'EM_MANUTENCAO', 1),
('SMT-03', 'Máquina de Serigrafia (Screen Printer)', 'SMT', 'Posto 01', 'OPERACIONAL', 1),
('TEST-01', 'Testador ICT (In-Circuit Test)', 'Testes Funcionais', 'Posto 01', 'PARADA', 1),
('TEST-02', 'Testador Funcional FCT 01', 'Testes Funcionais', 'Posto 02', 'OPERACIONAL', 1),
('TEST-03', 'Rack de Burn-in e Stress Térmico', 'Testes Funcionais', 'Posto 03', 'OPERACIONAL', 1),
('MONT-01', 'Esteira Automatizada de Montagem', 'Montagem Final', 'Posto 01', 'OPERACIONAL', 1),
('EMB-01', 'Encartuchadora Automática', 'Embalagem', 'Posto 01', 'OPERACIONAL', 1),
-- Máquinas também cadastradas no Controle da Qualidade (integração do ecossistema, OA3)
('INS-01', 'Bancada de Inserção Manual', 'Inserção Manual', 'Posto 01', 'OPERACIONAL', 1),
('QC-01', 'Bancada de Inspeção da Qualidade', 'Inspeção da Qualidade', 'Posto 01', 'OPERACIONAL', 1);

-- Catálogo de Peças Sobressalentes
INSERT INTO pecas (codigo_peca, nome, unidade_medida, ativo) VALUES
('PN-COR-100', 'Correia Dentada de Alimentador SMT', 'UN', 1),
('PN-SEN-030', 'Sensor Óptico de Posicionamento 24V', 'UN', 1),
('PN-RES-500', 'Resistência Tubular Forno de Refusão', 'UN', 1),
('PN-VAL-012', 'Válvula Solenoide Pneumática 5/2', 'UN', 1),
('PN-CAB-045', 'Cabo de Sonda ICT de Precisão', 'UN', 1),
('PN-ROL-608', 'Rolamento Blindado Esteira de Montagem', 'UN', 1),
('PN-VEN-120', 'Ventoinha Cooler Industrial 120mm', 'UN', 1);

-- Chamados Históricos e Atuais para Demonstração de KPIs
-- Chamado 1: Concluído (gerando downtime e MTTR)
INSERT INTO chamados_manutencao (
    equipamento_id, operador_abertura_id, tecnico_responsavel_id,
    prioridade, tipo_manutencao, status_chamado,
    descricao_falha, diagnostico_tecnico, causa_raiz,
    data_hora_abertura, data_hora_inicio_atendimento, data_hora_fim_atendimento, downtime_minutos
) VALUES (
    1, 1, 3,
    'ALTA', 'CORRETIVA', 'CONCLUIDO',
    'Travamento no feeder de alimentação de resistores.',
    'Correia do alimentador ressecada com desgaste excessivo.',
    'Desgaste mecânico / Fadiga de componente',
    datetime('now', '-2 days', '-4 hours'), datetime('now', '-2 days', '-3 hours', '-45 minutes'), datetime('now', '-2 days', '-3 hours'), 60
);

-- Chamado 2: Em andamento (SMT-02 com técnico trabalhando)
INSERT INTO chamados_manutencao (
    equipamento_id, operador_abertura_id, tecnico_responsavel_id,
    prioridade, tipo_manutencao, status_chamado,
    descricao_falha, diagnostico_tecnico, causa_raiz,
    data_hora_abertura, data_hora_inicio_atendimento
) VALUES (
    2, 1, 3,
    'CRITICA', 'CORRETIVA', 'EM_ANDAMENTO',
    'Oscilação de temperatura na Zona 4 do forno de refusão.',
    'Resistência 4 com falha intermitente no aquecimento.',
    'Falha elétrica em resistor de potência',
    datetime('now', '-1 hour'), datetime('now', '-35 minutes')
);

-- Chamado 3: Aberto aguardando atendimento (TEST-01 parada)
INSERT INTO chamados_manutencao (
    equipamento_id, operador_abertura_id,
    prioridade, tipo_manutencao, status_chamado,
    descricao_falha,
    data_hora_abertura
) VALUES (
    4, 2,
    'ALTA', 'CORRETIVA', 'ABERTO',
    'Erro de comunicação no barramento de sondas pneumáticas do ICT.',
    datetime('now', '-20 minutes')
);

-- Peças trocadas no Chamado 1
INSERT INTO chamado_pecas_trocadas (chamado_id, peca_id, quantidade) VALUES
(1, 1, 1.0);

-- Histórico de transições
INSERT INTO historico_status (equipamento_id, chamado_id, usuario_id, status_anterior, status_novo, alterado_em) VALUES
(1, 1, 1, 'OPERACIONAL', 'PARADA', datetime('now', '-2 days', '-4 hours')),
(1, 1, 3, 'PARADA', 'EM_MANUTENCAO', datetime('now', '-2 days', '-3 hours', '-45 minutes')),
(1, 1, 3, 'EM_MANUTENCAO', 'OPERACIONAL', datetime('now', '-2 days', '-3 hours')),
(2, 2, 1, 'OPERACIONAL', 'PARADA', datetime('now', '-1 hour')),
(2, 2, 3, 'PARADA', 'EM_MANUTENCAO', datetime('now', '-35 minutes')),
(4, 3, 2, 'OPERACIONAL', 'PARADA', datetime('now', '-20 minutes'));
