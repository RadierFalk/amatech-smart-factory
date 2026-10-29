"""API do Dashboard (api.py): chave, indicadores com semáforo, gráficos e paradas em andamento."""
import pytest
from fastapi.testclient import TestClient

import config
from api import app

CHAVE = {"X-API-Key": config.DASHBOARD_API_KEY}
DIA = "2026-08-15"   # exemplo do enunciado, já no script do banco


@pytest.fixture
def cliente(repo, monkeypatch):
    monkeypatch.setattr(config, "CAMINHO_BANCO", repo.caminho)   # as classes de serviço usam o banco do teste
    return TestClient(app)


def test_status_sem_chave_e_dados_com_chave(cliente):
    assert cliente.get("/api/status").json()["status"] == "online"
    assert cliente.get("/api/indicadores").status_code == 401
    assert cliente.get("/api/paradas-em-andamento", headers={"X-API-Key": "errada"}).status_code == 401


def test_indicadores_do_exemplo_do_enunciado(cliente):
    r = cliente.get(f"/api/indicadores?de={DIA}&ate=15/08/2026", headers=CHAVE).json()
    assert r["atendimento_meta"] == {"valor": 94.7, "unidade": "%", "semaforo": "amarelo"}
    assert r["indice_defeitos"]["valor"] == 4.2
    assert r["produtividade"]["valor"] == 215.7
    assert r["tempo_parada"]["minutos"] == 85
    assert r["producao"] == {"realizada": 1420, "aprovada": 1360, "reprovada": 60, "meta": 1500}


def test_filtro_por_turno_e_produto_pelo_nome(cliente):
    r = cliente.get(f"/api/indicadores?de={DIA}&ate={DIA}&turno=2&produto=Notebook modelo A", headers=CHAVE).json()
    assert r["producao"]["realizada"] == 0      # o exemplo é do 1º turno
    erro = cliente.get(f"/api/indicadores?de={DIA}&turno=Noturno", headers=CHAVE)
    assert erro.status_code == 422 and "Noturno" in erro.json()["detail"]


def test_periodo_invalido(cliente):
    assert cliente.get("/api/indicadores?de=2026-08-16&ate=2026-08-15", headers=CHAVE).status_code == 422
    assert cliente.get("/api/indicadores?de=ontem", headers=CHAVE).status_code == 422


def test_graficos_e_paradas_em_andamento(cliente):
    g = cliente.get(f"/api/graficos?de={DIA}&ate={DIA}", headers=CHAVE).json()
    assert g["defeitos_por_estacao"][0] == {"estacao": "Teste funcional", "quantidade": 45}
    assert cliente.get("/api/paradas-em-andamento", headers=CHAVE).json() == []
