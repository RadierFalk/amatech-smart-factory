"""Fixtures dos testes.

Testes marcados com a fixture `cliente` precisam de PostgreSQL em AMATECH_TEST_DATABASE_URL
(padrão: banco amatech_testes do docker-compose.dev.yml). Sem banco, eles são PULADOS, não falham.
O banco de testes é recriado do zero a cada execução: nunca aponte para o banco real.
"""
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import SCHEMAS_MODULOS, Base, obter_sessao
from app.core.rbac import Perfil
from app.core.seguranca import gerar_hash
from app.modelos import Usuario
from app.main import app

URL_TESTES = os.environ.get(
    "AMATECH_TEST_DATABASE_URL", "postgresql+psycopg://amatech:amatech@localhost:5432/amatech_testes"
)
SENHA = "senha-de-teste-123"


@pytest.fixture(scope="session")
def engine_testes():
    engine = create_engine(URL_TESTES)
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip(f"PostgreSQL de testes indisponível em {URL_TESTES} (suba o docker-compose.dev.yml)")
    with engine.begin() as conn:
        for schema in SCHEMAS_MODULOS:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sessao(engine_testes) -> Iterator[Session]:
    fabrica = sessionmaker(bind=engine_testes, expire_on_commit=False)
    with fabrica() as s:
        yield s
    # Isola cada teste: limpa todas as tabelas do ERP.
    tabelas = ", ".join(f'"{t.schema}"."{t.name}"' for t in Base.metadata.sorted_tables)
    with engine_testes.begin() as conn:
        conn.execute(text(f"TRUNCATE {tabelas} RESTART IDENTITY CASCADE"))


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
