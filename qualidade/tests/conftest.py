"""
Fixtures dos testes de login, permissões e migração. Tudo roda em banco temporário:
o banco do projeto nunca é aberto para escrita.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import autenticacao  # noqa: E402
import banco  # noqa: E402
import migracao  # noqa: E402

SENHA_INICIAL = "amatech1234"

ESQUEMA_LEGADO = """
CREATE TABLE produto (
    id_produto INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_serie_produto TEXT NOT NULL UNIQUE,
    modelo_produto TEXT NOT NULL
);
CREATE TABLE estacao (
    id_estacao INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_estacao TEXT NOT NULL UNIQUE,
    descricao_estacao TEXT
);
CREATE TABLE tipo_defeito (
    id_tipo_defeito INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_tipo_defeito TEXT NOT NULL UNIQUE,
    descricao_tipo_defeito TEXT
);
CREATE TABLE maquina (
    id_maquina INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_maquina TEXT NOT NULL UNIQUE,
    descricao_maquina TEXT
);
CREATE TABLE usuario (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_usuario TEXT NOT NULL,
    perfil_usuario TEXT NOT NULL
);
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
);
"""

# Os quatro usuários do banco antigo, mais um quinto que não corresponde a nenhuma conta do sistema novo
USUARIOS_LEGADOS = [
    ("João Silva", "Operador"),
    ("Maria Santos", "Responsavel_qualidade"),
    ("Carlos Oliveira", "Supervisor_producao"),
    ("Ana Souza", "Gestor"),
    ("Visitante Antigo", "Operador"),
]


def criar_banco_legado(caminho, com_usuarios=True):
    """Banco no formato anterior ao login (tabela usuario só com id, nome e perfil)."""
    conexao = sqlite3.connect(caminho)
    conexao.executescript(ESQUEMA_LEGADO)

    conexao.executemany("INSERT INTO produto (numero_serie_produto, modelo_produto) VALUES (?, ?)", [
        ("AMT-000001", "AMT N14"), ("AMT-000002", "AMT N15"), ("AMT-000003", "AMT N16"),
    ])
    conexao.executemany("INSERT INTO estacao (nome_estacao, descricao_estacao) VALUES (?, ?)", [
        ("Teste Funcional", "x"), ("Montagem Final", "y"),
    ])
    conexao.executemany("INSERT INTO tipo_defeito (nome_tipo_defeito, descricao_tipo_defeito) VALUES (?, ?)", [
        ("Tela", "x"), ("Bateria", "y"),
    ])
    conexao.executemany("INSERT INTO maquina (nome_maquina, descricao_maquina) VALUES (?, ?)", [
        ("TEST-01", "x"), ("SMT-01", "y"),
    ])

    if com_usuarios:
        conexao.executemany("INSERT INTO usuario (nome_usuario, perfil_usuario) VALUES (?, ?)", USUARIOS_LEGADOS)

        # (data, hora, classificação, situação, obs, ação, status, visibilidade, produto, estação, defeito, máquina, usuário)
        conexao.executemany("""
            INSERT INTO ocorrencia (
                data_ocorrencia, hora_ocorrencia, classificacao_defeito, situacao_produto,
                observacao_ocorrencia, acao_realizada, status_ocorrencia, visibilidade_ocorrencia,
                id_produto, id_estacao, id_tipo_defeito, id_maquina, id_usuario
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("2026-09-20", "08:30:00", "Maior", "Reprovado", "obs 1", "ação 1", "Aberta", "Visivel", 1, 1, 1, 1, 1),
            ("2026-09-21", "09:00:00", "Menor", "Aprovado", "obs 2", "ação 2", "Resolvida", "Visivel", 2, 2, 2, 2, 2),
            ("2026-09-22", "10:15:00", "Critico", "Em_reprocesso", "obs 3", "ação 3", "Em_analise", "Visivel", 3, 1, 2, 1, 3),
            ("2026-09-23", "11:45:00", "Menor", "Aprovado", "obs 4", "ação 4", "Aberta", "Oculta", 1, 2, 1, 2, 4),
            ("2026-09-24", "13:00:00", "Maior", "Reprovado", "obs 5", "ação 5", "Aberta", "Visivel", 2, 1, 2, 1, 5),
            ("2026-09-25", "14:20:00", "Menor", "Aprovado", "obs 6", "ação 6", "Resolvida", "Visivel", 3, 2, 1, 2, 1),
        ])

    conexao.commit()
    conexao.close()


@pytest.fixture
def banco_legado(tmp_path, monkeypatch):
    """Banco temporário no formato antigo, como estava antes do login."""
    caminho = tmp_path / "controle_qualidade.db"
    criar_banco_legado(caminho)
    monkeypatch.setattr(banco, "CAMINHO_BANCO", caminho)
    return caminho


@pytest.fixture
def banco_migrado(banco_legado):
    """O mesmo banco depois da migração (contas do login criadas)."""
    migracao.migrar()
    return banco_legado


@pytest.fixture
def entrar(banco_migrado):
    """entrar("ADM-0001") devolve o usuário da sessão, autenticando com a senha inicial."""
    def _entrar(matricula, senha=SENHA_INICIAL):
        usuario = autenticacao.autenticar(matricula, senha)
        assert usuario is not None, f"{matricula} deveria conseguir entrar"
        return usuario

    return _entrar


def ler_tabela(caminho, sql):
    conexao = sqlite3.connect(caminho)
    linhas = conexao.execute(sql).fetchall()
    conexao.close()
    return linhas
