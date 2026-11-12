"""Ambiente do Alembic: usa a mesma URL e os mesmos modelos da API."""
from alembic import context
from sqlalchemy import create_engine, text

from app.core.config import obter_configuracao
from app.core.db import SCHEMAS_MODULOS, Base
from app.modelos import *  # noqa: F401,F403 - registra todas as tabelas no Base.metadata

alvo_metadata = Base.metadata


def incluir_objeto(objeto, nome, tipo, refletido, comparado_a):
    # Só compara os schemas do ERP (ignora public e tabelas internas).
    if tipo == "table":
        return objeto.schema in SCHEMAS_MODULOS
    return True


def executar_offline() -> None:
    context.configure(
        url=obter_configuracao().database_url,
        target_metadata=alvo_metadata,
        literal_binds=True,
        include_schemas=True,
        include_object=incluir_objeto,
        version_table_schema="public",
    )
    with context.begin_transaction():
        context.run_migrations()


def executar_online() -> None:
    engine = create_engine(obter_configuracao().database_url)
    with engine.connect() as conn:
        for schema in SCHEMAS_MODULOS:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.commit()
        context.configure(
            connection=conn,
            target_metadata=alvo_metadata,
            include_schemas=True,
            include_object=incluir_objeto,
            version_table_schema="public",
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executar_offline()
else:
    executar_online()
