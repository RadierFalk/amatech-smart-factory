"""
Script de Inicialização do Banco de Dados SQLite do Sistema de Manutenção AMATECH
"""
import os
from database import DB_PATH, SCHEMA_PATH, ensure_database_initialized


def init_database(force_reset: bool = True) -> None:
    print(f"[*] Lendo esquema em: {SCHEMA_PATH}")
    print(f"[*] Inicializando banco SQLite em: {DB_PATH}")
    ensure_database_initialized(db_path=DB_PATH, force_reset=force_reset)
    print("[+] Banco de dados inicializado com sucesso!")


if __name__ == "__main__":
    init_database(force_reset=True)
