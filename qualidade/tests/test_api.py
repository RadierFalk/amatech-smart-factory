"""
Testes da API HTTP (FastAPI) do Controle da Qualidade.
Rodar:  python -m pytest tests -q
"""
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api  # noqa: E402
import banco  # noqa: E402

CHAVE = {"X-API-Key": api.CHAVE_API}


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    copia = tmp_path / "controle_qualidade.db"
    shutil.copy(banco.BANCO_INICIAL, copia)
    monkeypatch.setattr(banco, "CAMINHO_BANCO", copia)
    with TestClient(api.app) as c:
        yield c


def test_status_nao_precisa_de_chave(cliente):
    assert cliente.get("/api/status").json()["status"] == "online"


def test_ocorrencias_exigem_chave(cliente):
    # Na rede interna (Abordagem 1), rota de ocorrencias e acessivel sem chave:
    assert cliente.get("/api/ocorrencias").status_code == 200
    # Chave invalida informada continua sendo rejeitada:
    assert cliente.get("/api/ocorrencias", headers={"X-API-Key": "errada"}).status_code == 401
    ocorrencias = cliente.get("/api/ocorrencias", headers=CHAVE).json()
    assert ocorrencias and {"id_ocorrencia", "produto", "modelo_produto", "maquina"} <= set(ocorrencias[0])


def test_filtro_por_periodo(cliente):
    todas = cliente.get("/api/ocorrencias", headers=CHAVE).json()
    dia = todas[0]["data_ocorrencia"]
    do_dia = cliente.get(f"/api/ocorrencias?de={dia}&ate={dia}", headers=CHAVE).json()
    assert do_dia and all(o["data_ocorrencia"] == dia for o in do_dia)
    assert len(do_dia) < len(todas)


def test_banco_novo_comeca_com_os_dados_iniciais(tmp_path, monkeypatch):
    destino = tmp_path / "volume" / "controle_qualidade.db"
    monkeypatch.setattr(banco, "CAMINHO_BANCO", destino)
    banco.preparar_banco()
    assert destino.exists()
    assert len(banco.listar_produtos()) == 30
