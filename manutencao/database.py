"""
Camada de Acesso e Persistência em SQLite (manutencao.db).
Gerencia conexões, transações ACID e inicialização automática com seed data.
"""
import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH, MATRICULA_INTEGRACAO, SCHEMA_PATH


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Retorna uma conexão SQLite configurada com Row factory e Foreign Keys ativas."""
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager transacional para operações no banco SQLite."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_database_initialized(db_path: str | None = None, force_reset: bool = False) -> None:
    """
    Garante que o banco SQLite exista e esteja populado com a estrutura e dados iniciais
    definidos em docs/02_DATABASE_SCHEMA.sql.
    """
    target_path = db_path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    if force_reset and os.path.exists(target_path):
        conn = get_connection(target_path)
        try:
            conn.executescript(
                """
                PRAGMA foreign_keys = OFF;
                DROP TABLE IF EXISTS historico_status;
                DROP TABLE IF EXISTS chamado_pecas_trocadas;
                DROP TABLE IF EXISTS chamados_manutencao;
                DROP TABLE IF EXISTS pecas;
                DROP TABLE IF EXISTS equipamentos;
                DROP TABLE IF EXISTS usuarios;
                PRAGMA foreign_keys = ON;
                """
            )
            conn.commit()
        finally:
            conn.close()

    conn = get_connection(target_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios';"
        )
        tabela_existe = cursor.fetchone() is not None

        precisa_seed = True
        if tabela_existe:
            cursor.execute("SELECT COUNT(*) AS total FROM usuarios;")
            row = cursor.fetchone()
            if row and row["total"] > 0:
                precisa_seed = False

        if precisa_seed:
            if not os.path.exists(SCHEMA_PATH):
                raise FileNotFoundError(f"Arquivo de schema não encontrado: {SCHEMA_PATH}")
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                sql_script = f.read()
            cursor.executescript(sql_script)
            conn.commit()

        _migrar_integracao(conn)
    finally:
        conn.close()


def _migrar_integracao(conn: sqlite3.Connection) -> None:
    """
    Ajustes da integração com o ecossistema (OA3), aplicados também a bancos que já existiam.
    Idempotente: só acrescenta o que falta e nunca apaga dados.
    - origem_sistema e id_externo nos chamados (chamado aberto por outro sistema pela API, sem duplicar);
    - máquinas INS-01 e QC-01, usadas pelo Controle da Qualidade;
    - usuário de serviço "Integração" (inativo, não faz login), operador de abertura dos chamados da API.
    """
    colunas = {linha["name"] for linha in conn.execute("PRAGMA table_info(chamados_manutencao)")}
    if "origem_sistema" not in colunas:
        conn.execute("ALTER TABLE chamados_manutencao ADD COLUMN origem_sistema VARCHAR(50)")
    if "id_externo" not in colunas:
        conn.execute("ALTER TABLE chamados_manutencao ADD COLUMN id_externo VARCHAR(100)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_chamados_externo "
        "ON chamados_manutencao(origem_sistema, id_externo) WHERE id_externo IS NOT NULL"
    )
    conn.executemany(
        "INSERT OR IGNORE INTO equipamentos (codigo_tag, nome, setor, posto_trabalho) VALUES (?, ?, ?, 'Posto 01')",
        [
            ("INS-01", "Bancada de Inserção Manual", "Inserção Manual"),
            ("QC-01", "Bancada de Inspeção da Qualidade", "Inspeção da Qualidade"),
        ],
    )
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (nome, matricula, senha_hash, perfil, ativo) "
        "VALUES ('Integração (outros sistemas)', ?, '!', 'OPERADOR', 0)",
        (MATRICULA_INTEGRACAO,),
    )
    conn.commit()
