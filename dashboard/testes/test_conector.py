"""ConectorEcossistema com as APIs dos outros setores simuladas (não precisam estar no ar).

Horários das APIs em UTC: 13:00Z = 09:00 em Manaus (1º turno); 02:30Z = 22:30 do dia anterior (fora dos turnos).
"""
from datetime import date

import pytest
import requests

import config
from servicos.conector_ecossistema import ConectorEcossistema, utc_para_local

DIA = date(2026, 10, 27)

MODELOS = [{"codigo": "N14-I5-8-256", "nome": "AMT N14"}, {"codigo": "N15-I5-8-512", "nome": "AMT N15"}]
EQUIPAMENTOS = [{"codigo_tag": "TEST-01", "nome": "Testador ICT", "setor": "Testes Funcionais"},
                {"codigo_tag": "QC-01", "nome": "Bancada de inspeção", "setor": "Inspeção da Qualidade"},
                {"codigo_tag": "XYZ-01", "nome": "Robô de pintura", "setor": "Pintura"}]
PASSAGENS = [
    {"numero_serie": "AMT-000001", "modelo": MODELOS[0], "status": "Aprovado", "em": "2026-10-27T13:00:00Z"},
    {"numero_serie": "AMT-000006", "modelo": MODELOS[0], "status": "Reprovado", "em": "2026-10-27T13:20:00Z"},
    {"numero_serie": "AMT-000011", "modelo": MODELOS[0], "status": "Em Teste", "em": "2026-10-27T13:30:00Z"},
    {"numero_serie": "AMT-000002", "modelo": MODELOS[1], "status": "Aprovado", "em": "2026-10-28T02:30:00Z"},
]


def ocorrencia(id_ocorrencia, situacao="Reprovado", modelo="AMT N14", hora="09:20:00"):
    return {"id_ocorrencia": id_ocorrencia, "data_ocorrencia": "2026-10-27", "hora_ocorrencia": hora,
            "produto": "AMT-000006", "modelo_produto": modelo, "tipo_defeito": "Teclado",
            "estacao": "Inspeção de Qualidade", "maquina": "QC-01", "observacao_ocorrencia": "Teclas sem resposta",
            "acao_realizada": "Troca do teclado", "situacao_produto": situacao}


def chamado(id_chamado, status="CONCLUIDO", fim="2026-10-27T14:25:00Z", tipo="CORRETIVA"):
    return {"id_chamado": id_chamado, "equipamento_tag": "TEST-01", "setor": "Testes Funcionais",
            "tipo_manutencao": tipo, "status_chamado": status, "descricao_falha": "Sonda ICT quebrada",
            "data_hora_abertura": "2026-10-27T13:00:00Z", "data_hora_fim": fim}


class Resposta:
    def __init__(self, dados, status_code=200):
        self.dados, self.status_code = dados, status_code

    def json(self):
        return self.dados


class ApisFalsas:
    """Responde como os três sistemas. Um sistema em `fora_do_ar` não responde."""

    def __init__(self):
        self.dados = {"/api/v1/produtos": MODELOS, "/api/equipamentos": EQUIPAMENTOS, "/api/v1/passagens": PASSAGENS,
                      "/api/ocorrencias": [ocorrencia(1), ocorrencia(2, "Em_reprocesso")],
                      "/api/manutencao/chamados": [chamado(1), chamado(2, status="CANCELADO")]}
        self.fora_do_ar = set()

    def get(self, url, params=None, headers=None, timeout=None):
        for caminho, dados in self.dados.items():
            if url.endswith(caminho):
                if any(url.startswith(base) for base in self.fora_do_ar):
                    raise requests.ConnectionError()
                return Resposta(dados)
        return Resposta({}, 404)


@pytest.fixture
def apis():
    return ApisFalsas()


@pytest.fixture
def conector(repo, apis):
    return ConectorEcossistema(repo, http=apis)


def contar(repo, tabela):
    return repo.consultar_um(f"SELECT COUNT(*) AS n FROM {tabela} WHERE origem_sistema IS NOT NULL")["n"]


def test_converte_utc_para_o_horario_da_fabrica():
    assert utc_para_local("2026-10-27T13:00:00Z").hour == 13 + config.FUSO_HORAS
    assert utc_para_local("2026-10-27 13:00:00").hour == 9   # Manutenção antiga, sem o Z


def test_sincroniza_os_tres_setores(repo, conector, supervisor):
    resultados = {r.setor: r for r in conector.sincronizar(DIA, DIA, supervisor)}
    assert [resultados[s].status for s in ("rastreabilidade", "qualidade", "manutencao")] == ["concluida"] * 3

    producao = repo.consultar_um("SELECT * FROM registro_producao WHERE origem_sistema = 'rastreabilidade'")
    assert (producao["data"], producao["id_turno"]) == ("2026-10-27", 1)
    assert (producao["qtd_realizada"], producao["qtd_aprovada"], producao["qtd_reprovada"]) == (2, 1, 1)
    assert any("fora dos turnos" in i for i in resultados["rastreabilidade"].ignorados)   # 22:30 do dia 27
    assert any("XYZ-01" in i for i in resultados["rastreabilidade"].ignorados)           # setor sem estação

    assert contar(repo, "defeito") == 2
    assert contar(repo, "retrabalho") == 1   # só a ocorrência em reprocesso
    parada = repo.consultar_um("SELECT * FROM parada WHERE origem_sistema = 'manutencao'")
    assert (parada["inicio"], parada["fim"], parada["id_externo"]) == ("2026-10-27 09:00", "2026-10-27 10:25", "MNT-1")
    assert any("cancelado" in i for i in resultados["manutencao"].ignorados)


def test_sincronizar_de_novo_atualiza_sem_duplicar(repo, conector, apis, supervisor):
    apis.dados["/api/manutencao/chamados"] = [chamado(1, status="EM_ANDAMENTO", fim=None)]
    conector.sincronizar(DIA, DIA, supervisor)
    assert repo.consultar_um("SELECT fim FROM parada WHERE id_externo = 'MNT-1'")["fim"] is None
    apis.dados["/api/manutencao/chamados"] = [chamado(1)]   # o chamado foi concluído
    conector.sincronizar(DIA, DIA, supervisor)
    assert repo.consultar_um("SELECT fim FROM parada WHERE id_externo = 'MNT-1'")["fim"] == "2026-10-27 10:25"
    assert (contar(repo, "registro_producao"), contar(repo, "defeito"), contar(repo, "parada")) == (1, 2, 1)


def test_defeito_sem_producao_recusa_so_o_setor_da_qualidade(repo, conector, apis, supervisor):
    apis.dados["/api/ocorrencias"] = [ocorrencia(1), ocorrencia(3, modelo="AMT N15")]   # N15 não produziu às 9h
    resultados = {r.setor: r for r in conector.sincronizar(DIA, DIA, supervisor)}
    assert resultados["qualidade"].status == "rejeitada"
    assert resultados["qualidade"].erros[0][:2] == (3, "data")
    assert contar(repo, "defeito") == 0                                # RN06: nada da Qualidade foi gravado
    assert resultados["rastreabilidade"].status == resultados["manutencao"].status == "concluida"


def test_sistema_fora_do_ar_vira_aviso(repo, conector, apis, supervisor):
    apis.fora_do_ar = {config.QUALIDADE_URL, config.MANUTENCAO_URL}
    resultados = {r.setor: r for r in conector.sincronizar(DIA, DIA, supervisor)}
    assert resultados["rastreabilidade"].status == "concluida"
    assert resultados["qualidade"].status == resultados["manutencao"].status == "fora_do_ar"
    assert repo.consultar_um("SELECT COUNT(*) AS n FROM importacao")["n"] == 1   # só a da Rastreabilidade


def test_periodo_sem_dados_nao_registra_importacao(repo, conector, supervisor):
    resultados = conector.sincronizar(date(2026, 1, 1), date(2026, 1, 1), supervisor)
    assert {r.status for r in resultados if r.setor != "rastreabilidade"} == {"sem_dados"}
    assert repo.consultar_um("SELECT COUNT(*) AS n FROM importacao")["n"] == 0
