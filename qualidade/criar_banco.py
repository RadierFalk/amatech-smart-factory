import sqlite3
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO
# ============================================================

PASTA_BANCO = Path("banco")
ARQUIVO_BANCO = PASTA_BANCO / "controle_qualidade.db"

PASTA_BANCO.mkdir(exist_ok=True)

conn = sqlite3.connect(ARQUIVO_BANCO)
cursor = conn.cursor()

# Ativa integridade das chaves estrangeiras
cursor.execute("PRAGMA foreign_keys = ON")


# ============================================================
# LIMPEZA — permite executar o script novamente
# ============================================================

cursor.execute("DROP TABLE IF EXISTS ocorrencia")
cursor.execute("DROP TABLE IF EXISTS usuario")
cursor.execute("DROP TABLE IF EXISTS maquina")
cursor.execute("DROP TABLE IF EXISTS tipo_defeito")
cursor.execute("DROP TABLE IF EXISTS estacao")
cursor.execute("DROP TABLE IF EXISTS produto")


# ============================================================
# TABELA: PRODUTO
# ============================================================

cursor.execute("""
CREATE TABLE produto (
    id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_serie_produto TEXT NOT NULL UNIQUE,
    modelo_produto TEXT NOT NULL
)
""")


# ============================================================
# TABELA: ESTACAO
# ============================================================

cursor.execute("""
CREATE TABLE estacao (
    id_estacao INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_estacao TEXT NOT NULL UNIQUE,
    descricao_estacao TEXT
)
""")


# ============================================================
# TABELA: TIPO_DEFEITO
# ============================================================

cursor.execute("""
CREATE TABLE tipo_defeito (
    id_tipo_defeito INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_tipo_defeito TEXT NOT NULL UNIQUE,
    descricao_tipo_defeito TEXT
)
""")


# ============================================================
# TABELA: MAQUINA
# ============================================================

cursor.execute("""
CREATE TABLE maquina (
    id_maquina INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_maquina TEXT NOT NULL UNIQUE,
    descricao_maquina TEXT
)
""")


# ============================================================
# TABELA: USUARIO
# ============================================================

cursor.execute("""
CREATE TABLE usuario (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_usuario TEXT NOT NULL,
    perfil_usuario TEXT NOT NULL
)
""")


# ============================================================
# TABELA: OCORRENCIA
# ============================================================

cursor.execute("""
CREATE TABLE ocorrencia (
    id_ocorrencia INTEGER PRIMARY KEY AUTOINCREMENT,
    data_ocorrencia DATE NOT NULL,
    hora_ocorrencia TIME NOT NULL,
    classificacao_defeito TEXT NOT NULL,
    situacao_produto TEXT NOT NULL,
    observacao_ocorrencia TEXT,
    acao_realizada TEXT,
    status_ocorrencia TEXT NOT NULL,
    visibilidade_ocorrencia TEXT NOT NULL DEFAULT 'Visivel',

    id_produto INTEGER NOT NULL,
    id_estacao INTEGER NOT NULL,
    id_tipo_defeito INTEGER NOT NULL,
    id_maquina INTEGER NOT NULL,
    id_usuario INTEGER NOT NULL,

    FOREIGN KEY (id_produto) REFERENCES produto(id_produto),
    FOREIGN KEY (id_estacao) REFERENCES estacao(id_estacao),
    FOREIGN KEY (id_tipo_defeito) REFERENCES tipo_defeito(id_tipo_defeito),
    FOREIGN KEY (id_maquina) REFERENCES maquina(id_maquina),
    FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
)
""")


# ============================================================
# DADOS INICIAIS — PRODUTOS
# ============================================================

# Mesmos números de série e modelos da Rastreabilidade (dona desse cadastro): AMT-000001 a AMT-000030,
# com os modelos AMT N14 a N18 distribuídos em rodízio. Com o sistema da Rastreabilidade no ar, a tela
# busca também os notebooks novos (integracao.py).
MODELOS_RASTREABILIDADE = ["AMT N14", "AMT N15", "AMT N16", "AMT N17", "AMT N18"]

produtos = [
    (f"AMT-{numero:06d}", MODELOS_RASTREABILIDADE[(numero - 1) % len(MODELOS_RASTREABILIDADE)])
    for numero in range(1, 31)
]

cursor.executemany("""
INSERT INTO produto (
    numero_serie_produto,
    modelo_produto
)
VALUES (?, ?)
""", produtos)


# ============================================================
# DADOS INICIAIS — ESTAÇÕES
# ============================================================

estacoes = [
    ("SMT", "Montagem de componentes eletrônicos"),
    ("Inserção Manual", "Inserção manual de componentes"),
    ("Montagem Final", "Montagem final do notebook"),
    ("Instalação de Software", "Instalação e configuração do software"),
    ("Teste Funcional", "Testes funcionais do produto"),
    ("Inspeção de Qualidade", "Inspeção e controle da qualidade"),
    ("Embalagem", "Embalagem do produto final"),
]

cursor.executemany("""
INSERT INTO estacao (
    nome_estacao,
    descricao_estacao
)
VALUES (?, ?)
""", estacoes)


# ============================================================
# DADOS INICIAIS — TIPOS DE DEFEITO
# ============================================================

tipos_defeito = [
    ("Tela", "Falhas relacionadas à tela ou imagem"),
    ("Teclado", "Falhas relacionadas ao teclado"),
    ("Touchpad", "Falhas relacionadas ao touchpad"),
    ("USB", "Falhas relacionadas às portas USB"),
    ("Áudio", "Falhas relacionadas ao sistema de áudio"),
    ("Wi-Fi", "Falhas relacionadas à conectividade Wi-Fi"),
    ("Câmera", "Falhas relacionadas à câmera"),
    ("Bateria", "Falhas relacionadas à bateria"),
    ("Armazenamento", "Falhas relacionadas ao armazenamento"),
    ("Desempenho", "Falhas relacionadas ao desempenho"),
    ("Montagem", "Falhas relacionadas à montagem física"),
    ("Software", "Falhas relacionadas ao software"),
]

cursor.executemany("""
INSERT INTO tipo_defeito (
    nome_tipo_defeito,
    descricao_tipo_defeito
)
VALUES (?, ?)
""", tipos_defeito)


# ============================================================
# DADOS INICIAIS — MÁQUINAS
# ============================================================

# TAGs da Manutenção (dona das máquinas). As seis primeiras mantêm a ordem antiga, usada pelas ocorrências abaixo.
maquinas = [
    ("SMT-01", "Máquina da linha SMT 01"),
    ("INS-01", "Equipamento da estação de inserção manual"),
    ("MONT-01", "Equipamento da montagem final"),
    ("TEST-01", "Estação automática de testes funcionais"),
    ("TEST-02", "Estação automática de testes funcionais"),
    ("QC-01", "Equipamento utilizado na inspeção de qualidade"),
    ("SMT-02", "Forno de Refusão 10 Zonas"),
    ("SMT-03", "Máquina de Serigrafia (Screen Printer)"),
    ("TEST-03", "Rack de Burn-in e Stress Térmico"),
    ("EMB-01", "Encartuchadora Automática"),
]

cursor.executemany("""
INSERT INTO maquina (
    nome_maquina,
    descricao_maquina
)
VALUES (?, ?)
""", maquinas)


# ============================================================
# DADOS INICIAIS — USUÁRIOS
# ============================================================

usuarios = [
    ("João Silva", "Operador"),
    ("Maria Santos", "Responsavel_qualidade"),
    ("Carlos Oliveira", "Supervisor_producao"),
    ("Ana Souza", "Gestor"),
]

cursor.executemany("""
INSERT INTO usuario (
    nome_usuario,
    perfil_usuario
)
VALUES (?, ?)
""", usuarios)


# ============================================================
# DADOS INICIAIS — OCORRÊNCIAS
# ============================================================

ocorrencias = [
    (
        "2026-09-28", "08:15",
        "Maior", "Reprovado",
        "Tela apresentou falhas durante o teste.",
        "Produto encaminhado para reprocesso.",
        "Em_analise", "Visivel",
        1, 5, 1, 4, 1
    ),
    (
        "2026-09-28", "09:40",
        "Menor", "Em_reprocesso",
        "Tecla apresentou falha de funcionamento.",
        "Substituição do componente.",
        "Resolvida", "Visivel",
        2, 3, 2, 3, 2
    ),
    (
        "2026-09-28", "10:25",
        "Critico", "Reprovado",
        "Falha no teste de bateria.",
        "Produto retirado da linha para análise.",
        "Aberta", "Visivel",
        3, 5, 8, 4, 1
    ),
    (
        "2026-09-29", "11:10",
        "Maior", "Reprovado",
        "Falha de conexão Wi-Fi.",
        "Reprocessamento do produto.",
        "Em_analise", "Visivel",
        4, 5, 6, 5, 2
    ),
    (
        "2026-09-29", "13:30",
        "Menor", "Aprovado",
        "Pequena inconsistência identificada na montagem.",
        "Ajuste realizado.",
        "Resolvida", "Visivel",
        5, 6, 11, 6, 2
    ),
    (
        "2026-09-29", "14:45",
        "Maior", "Reprovado",
        "Câmera não apresentou imagem.",
        "Produto encaminhado para análise.",
        "Aberta", "Visivel",
        6, 5, 7, 4, 1
    ),
    (
        "2026-09-30", "08:50",
        "Menor", "Em_reprocesso",
        "Problema identificado durante instalação.",
        "Reinstalação do software.",
        "Resolvida", "Visivel",
        7, 4, 12, 4, 1
    ),
    (
        "2026-09-30", "10:20",
        "Critico", "Reprovado",
        "Falha no armazenamento detectada no teste.",
        "Produto encaminhado para manutenção.",
        "Em_analise", "Oculta",
        8, 5, 9, 5, 2
    ),
]

cursor.executemany("""
INSERT INTO ocorrencia (
    data_ocorrencia,
    hora_ocorrencia,
    classificacao_defeito,
    situacao_produto,
    observacao_ocorrencia,
    acao_realizada,
    status_ocorrencia,
    visibilidade_ocorrencia,
    id_produto,
    id_estacao,
    id_tipo_defeito,
    id_maquina,
    id_usuario
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", ocorrencias)


# ============================================================
# FINALIZAÇÃO
# ============================================================

conn.commit()

print("=" * 50)
print("BANCO DE DADOS CRIADO COM SUCESSO!")
print("=" * 50)
print(f"Arquivo: {ARQUIVO_BANCO}")
print()

# Verificação das tabelas
cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name
""")

print("Tabelas:")
for tabela in cursor.fetchall():
    print(f" - {tabela[0]}")

cursor.execute("SELECT COUNT(*) FROM ocorrencia")
print()
print(f"Ocorrências cadastradas: {cursor.fetchone()[0]}")

conn.close()