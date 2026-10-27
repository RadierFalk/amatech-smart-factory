"""
Camada de Acesso e Persistência em SQLite (manutencao.db).
Gerencia conexões, transações ACID e inicialização automática com seed data.
"""
import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH, SCHEMA_PATH


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
    finally:
        conn.close()
