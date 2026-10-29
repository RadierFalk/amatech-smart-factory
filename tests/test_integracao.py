"""
Testes da integração com a Rastreabilidade e a Manutenção (integracao.py).
As chamadas HTTP são simuladas, então os outros sistemas não precisam estar no ar.
Rodar:  python -m pytest tests -q
"""
import shutil
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import banco  # noqa: E402
import integracao  # noqa: E402


class Chamadas(list):
    """Requisições feitas pela integração; `respostas` diz o que devolver para cada trecho de URL."""

    def __init__(self):
        super().__init__()
        self.respostas = {}


class RespostaFalsa:
    def __init__(self, status_code, dados):
        self.status_code = status_code
        self._dados = dados

    def json(self):
        return self._dados


@pytest.fixture
def chamadas(tmp_path, monkeypatch):
    """Banco temporário (cópia do oficial) e registro das requisições feitas pela integração."""
    copia = tmp_path / "controle_qualidade.db"
    shutil.copy(banco.CAMINHO_BANCO, copia)
    monkeypatch.setattr(banco, "CAMINHO_BANCO", copia)

    feitas = Chamadas()

    def requisicao(metodo, url, json=None, headers=None, timeout=None):
        feitas.append((metodo, url, json))
        for trecho, resposta in feitas.respostas.items():
            if trecho in url:
                return resposta
        raise requests.ConnectionError()   # URL sem resposta combinada: sistema fora do ar

    monkeypatch.setattr(integracao.requests, "request", requisicao)
    return feitas


def registrar(situacao, serie="AMT-000017", maquina="TEST-02"):
    produto = next(p for p in banco.listar_produtos() if p["numero_serie_produto"] == serie)
    equipamento = next(m for m in banco.listar_maquinas() if m["nome_maquina"] == maquina)
    return banco.registrar_ocorrencia("2026-10-28", "10:00:00", "Critico", situacao, "Teclas sem resposta",
                                      "Troca do teclado", "Aberta", produto["id_produto"], 5, 2,
                                      equipamento["id_maquina"], 1)


def test_cadastros_seguem_os_setores_donos():
    series = [p["numero_serie_produto"] for p in banco.listar_produtos()]
    maquinas = {m["nome_maquina"] for m in banco.listar_maquinas()}
    assert "AMT-000001" in series and "AMT-000030" in series
    assert {"SMT-01", "INS-01", "TEST-01", "QC-01", "EMB-01"} <= maquinas


def test_reprovado_envia_a_falha_real(chamadas):
    chamadas.respostas["/status"] = RespostaFalsa(200, {"alterado": True, "status": "Reprovado"})
    id_ocorrencia = registrar("Reprovado")
    assert integracao.notificar_ocorrencia(id_ocorrencia)[0][0] == "sucesso"
    metodo, url, corpo = chamadas[0]
    assert url.endswith("/api/v1/producoes/AMT-000017/status")
    assert corpo["status"] == "Reprovado"
    assert corpo["descricao_falha"] == "Teclas sem resposta"
    assert corpo["id_externo"] == f"QLD-{id_ocorrencia}"


def test_reprocesso_reprova_e_devolve_para_a_montagem(chamadas):
    chamadas.respostas["/status"] = RespostaFalsa(200, {"alterado": True, "status": "?"})
    integracao.notificar_ocorrencia(registrar("Em_reprocesso"))
    assert [corpo["status"] for _, _, corpo in chamadas] == ["Reprovado", "Em Montagem"]


def test_abre_chamado_com_prioridade_pela_classificacao(chamadas):
    chamadas.respostas["/status"] = RespostaFalsa(200, {"alterado": True, "status": "Reprovado"})
    chamadas.respostas["/api/manutencao/chamados"] = RespostaFalsa(201, {"id_chamado": 7, "criado": True})
    mensagens = integracao.notificar_ocorrencia(registrar("Reprovado"), abrir_chamado=True)
    assert mensagens[1] == ("sucesso", "Manutenção: chamado #7 aberto para a máquina TEST-02.")
    corpo = chamadas[-1][2]
    assert (corpo["equipamento_tag"], corpo["prioridade"], corpo["origem_sistema"]) == ("TEST-02", "CRITICA",
                                                                                         "qualidade")


def test_sistema_fora_do_ar_vira_aviso(chamadas):
    mensagens = integracao.notificar_ocorrencia(registrar("Reprovado"), abrir_chamado=True)
    assert [tipo for tipo, _ in mensagens] == ["aviso", "aviso"]
    assert all("fora do ar" in mensagem for _, mensagem in mensagens)
    assert [tipo for tipo, _ in integracao.sincronizar_cadastros()] == ["aviso", "aviso"]


def test_erro_da_manutencao_aparece_na_mensagem(chamadas):
    chamadas.respostas["/status"] = RespostaFalsa(200, {"alterado": False, "status": "Reprovado"})
    chamadas.respostas["/api/manutencao/chamados"] = RespostaFalsa(409, {"detail": "Bloqueio de Redundância (RN02)"})
    mensagens = integracao.notificar_ocorrencia(registrar("Reprovado"), abrir_chamado=True)
    assert mensagens[0] == ("sucesso", "Rastreabilidade: a reprovação de AMT-000017 já estava registrada.")
    assert mensagens[1] == ("aviso", "Manutenção: o chamado não foi aberto (Bloqueio de Redundância (RN02)).")
