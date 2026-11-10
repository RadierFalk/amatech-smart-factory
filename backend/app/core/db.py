"""Conexão com o PostgreSQL via SQLAlchemy 2.0.

Um único banco `amatech`, com um schema por módulo: usr, ras, qld, mnt, dsh.
"""
from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import obter_configuracao

SCHEMAS_MODULOS = ("usr", "ras", "qld", "mnt", "dsh")

# Nomes previsíveis para constraints e índices: o Alembic gera migrações estáveis com isso.
CONVENCAO_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_NOMES)


engine = create_engine(obter_configuracao().database_url, pool_pre_ping=True)
SessaoLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def obter_sessao() -> Iterator[Session]:
    """Dependência do FastAPI: uma sessão por requisição, com commit no sucesso e rollback no erro."""
    sessao = SessaoLocal()
    try:
        yield sessao
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    finally:
        sessao.close()
