"""Fixtures dos testes.

Banco usado pelos testes que precisam de banco (fixtures `sessao` e `cliente`):
1. AMATECH_TEST_DATABASE_URL, se definida (o CI define, com PostgreSQL). Se ela não responder, os testes são PULADOS.
2. Sem a variável: o PostgreSQL do docker-compose.dev.yml (banco amatech_testes).
3. Sem o PostgreSQL no ar: SQLite em memória, só para desenvolver numa máquina sem Docker.
   Ele cobre as regras de negócio, mas NÃO substitui o Postgres: o CI roda tudo no Postgres e falha se algo for pulado.
   Testes que dependem de comportamento exclusivo do Postgres usam a marca @pytest.mark.postgres.

O banco de testes é recriado do zero a cada execução: nunca aponte para o banco real.
"""
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import SCHEMAS_MODULOS, Base, obter_sessao
from app.core.rbac import Perfil
from app.core.seguranca import gerar_hash
from app.modelos import Usuario
from app.main import app

URL_EXPLICITA = os.environ.get("AMATECH_TEST_DATABASE_URL")
URL_PADRAO = "postgresql+psycopg://amatech:amatech@localhost:5432/amatech_testes"
SENHA = "senha-de-teste-123"


def pytest_configure(config):
    config.addinivalue_line("markers", "postgres: teste que só faz sentido no PostgreSQL (pulado no SQLite local)")


def _engine_sqlite():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _anexar_schemas(conexao, _):
        for schema in SCHEMAS_MODULOS:
            conexao.execute(f"ATTACH DATABASE ':memory:' AS {schema}")
        conexao.execute("PRAGMA foreign_keys = ON")

    return engine


def _conecta(engine) -> bool:
    try:
        with engine.connect():
            return True
    except OperationalError:
        return False


@pytest.fixture(scope="session")
def engine_testes():
    if URL_EXPLICITA:
        engine = create_engine(URL_EXPLICITA)
        if not _conecta(engine):
            pytest.skip(f"Banco de testes indisponível em {URL_EXPLICITA}")
    else:
        engine = create_engine(URL_PADRAO, connect_args={"connect_timeout": 2})
        if not _conecta(engine):
            engine = _engine_sqlite()

    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            for schema in SCHEMAS_MODULOS:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
                conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _pular_marcados_postgres(request):
    if request.node.get_closest_marker("postgres"):
        engine = request.getfixturevalue("engine_testes")
        if engine.dialect.name != "postgresql":
            pytest.skip("Comportamento exclusivo do PostgreSQL")


@pytest.fixture
def sessao(engine_testes) -> Iterator[Session]:
    fabrica = sessionmaker(bind=engine_testes, expire_on_commit=False)
    with fabrica() as s:
        yield s
    # Isola cada teste: limpa todas as tabelas do ERP.
    tabelas = Base.metadata.sorted_tables
    with engine_testes.begin() as conn:
        if engine_testes.dialect.name == "postgresql":
            nomes = ", ".join(f'"{t.schema}"."{t.name}"' for t in tabelas)
            conn.execute(text(f"TRUNCATE {nomes} RESTART IDENTITY CASCADE"))
        else:
            for t in reversed(tabelas):
                conn.execute(t.delete())


@pytest.fixture
def cliente(engine_testes, sessao) -> Iterator[TestClient]:
    fabrica = sessionmaker(bind=engine_testes, expire_on_commit=False)

    def sessao_teste():
        s = fabrica()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    app.dependency_overrides[obter_sessao] = sessao_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def criar_usuario(sessao):
    def _criar(matricula: str, perfil: Perfil, ativo: bool = True, nome: str = "Teste") -> Usuario:
        u = Usuario(matricula=matricula, nome=nome, senha_hash=gerar_hash(SENHA), perfil=perfil.value, ativo=ativo)
        sessao.add(u)
        sessao.commit()
        return u

    return _criar


@pytest.fixture
def token_de(cliente):
    def _token(matricula: str) -> dict[str, str]:
        r = cliente.post("/api/auth/login", json={"matricula": matricula, "senha": SENHA})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _token
