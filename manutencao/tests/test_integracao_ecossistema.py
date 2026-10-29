"""
Testes da integração com o ecossistema (OA3): migração idempotente, abertura de chamado por outro sistema
(POST /api/manutencao/chamados) e datas em UTC com "Z" no GET.
"""
import os
import sqlite3
import tempfile

import pytest
from fastapi.testclient import TestClient

import database
from api import app
from config import API_KEY_INTEGRACAO
from database import ensure_database_initialized

CHAVE = {"X-API-Key": API_KEY_INTEGRACAO}


@pytest.fixture
def cliente(monkeypatch):
    """API apontando para um banco temporário com o seed oficial."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    ensure_database_initialized(db_path=path, force_reset=True)
    monkeypatch.setattr(database, "DB_PATH", path)
    with TestClient(app) as c:
        yield c
    os.remove(path)


def test_migracao_em_banco_antigo_e_idempotente():
    """Um banco criado antes da integração (sem as colunas novas) recebe os ajustes, e rodar de novo não duplica."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, matricula TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL, perfil TEXT NOT NULL, ativo BOOLEAN NOT NULL DEFAULT 1);
        CREATE TABLE equipamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo_tag TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL, setor TEXT NOT NULL, posto_trabalho TEXT,
            status_operacional TEXT NOT NULL DEFAULT 'OPERACIONAL', ativo BOOLEAN NOT NULL DEFAULT 1);
        CREATE TABLE chamados_manutencao (id INTEGER PRIMARY KEY AUTOINCREMENT, equipamento_id INTEGER NOT NULL,
            descricao_falha TEXT NOT NULL);
        INSERT INTO usuarios (nome, matricula, senha_hash, perfil) VALUES ('Ana', 'OP-1', '123456', 'OPERADOR');
        """
    )
    conn.commit()
    conn.close()
    ensure_database_initialized(db_path=path)
    ensure_database_initialized(db_path=path)
    conn = sqlite3.connect(path)
    colunas = {linha[1] for linha in conn.execute("PRAGMA table_info(chamados_manutencao)")}
    tags = [linha[0] for linha in conn.execute("SELECT codigo_tag FROM equipamentos ORDER BY codigo_tag")]
    servico = conn.execute("SELECT ativo FROM usuarios WHERE matricula = 'SVC-INTEGRACAO'").fetchall()
    conn.close()
    os.remove(path)
    assert {"origem_sistema", "id_externo"} <= colunas
    assert tags == ["INS-01", "QC-01"]
    assert servico == [(0,)]


def test_chamado_aberto_pela_qualidade_nao_duplica(cliente):
    corpo = {"equipamento_tag": "qc-01", "descricao_falha": "Câmera de inspeção desalinhada",
             "prioridade": "ALTA", "origem_sistema": "Qualidade", "id_externo": "QLD-42"}
    r = cliente.post("/api/manutencao/chamados", json=corpo, headers=CHAVE)
    assert r.status_code == 201 and r.json()["criado"] is True
    de_novo = cliente.post("/api/manutencao/chamados", json=corpo, headers=CHAVE)
    assert de_novo.status_code == 200
    assert de_novo.json() == {"id_chamado": r.json()["id_chamado"], "criado": False}

    chamado = next(c for c in cliente.get("/api/manutencao/chamados", headers=CHAVE).json()
                   if c["id_chamado"] == r.json()["id_chamado"])
    assert (chamado["origem_sistema"], chamado["id_externo"]) == ("qualidade", "QLD-42")
    assert chamado["operador"] == "Integração (outros sistemas)"
    assert chamado["data_hora_abertura"].endswith("Z")
    maquina = next(e for e in cliente.get("/api/equipamentos", headers=CHAVE).json() if e["codigo_tag"] == "QC-01")
    assert maquina["status_operacional"] == "PARADA"


def test_erros_da_abertura_externa(cliente):
    corpo = {"equipamento_tag": "TEST-01", "descricao_falha": "Falha no testador", "origem_sistema": "qualidade"}
    assert cliente.post("/api/manutencao/chamados", json=corpo).status_code == 401
    assert cliente.post("/api/manutencao/chamados", json=corpo, headers={"X-API-Key": "errada"}).status_code == 401
    assert cliente.post("/api/manutencao/chamados", json=corpo, headers=CHAVE).status_code == 409   # já PARADA (RN02)
    corpo["equipamento_tag"] = "XYZ-99"
    assert cliente.post("/api/manutencao/chamados", json=corpo, headers=CHAVE).status_code == 404
    corpo.update(equipamento_tag="EMB-01", prioridade="URGENTE")
    assert cliente.post("/api/manutencao/chamados", json=corpo, headers=CHAVE).status_code == 422


def test_leituras_exigem_chave_e_status_nao(cliente):
    assert cliente.get("/api/status").status_code == 200
    for rota in ("/api/equipamentos", "/api/manutencao/chamados", "/api/manutencao/indicadores"):
        assert cliente.get(rota).status_code == 401
        assert cliente.get(rota, headers=CHAVE).status_code == 200
