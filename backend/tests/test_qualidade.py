"""Testes do módulo de Qualidade (/api/qld).

Portam as regras de qualidade/ocorrencia.py e permissoes.py (responsável é quem registra, ocultar em vez de
apagar, matriz por perfil) e cobrem a abertura de chamado na Manutenção, agora dentro da mesma API.
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core import tempo
from app.core.rbac import Perfil
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.rastreabilidade.constantes import ETAPAS_PADRAO
from app.modulos.rastreabilidade.modelos import Etapa, Modelo, Producao

AGORA = datetime(2026, 11, 12, 15, 0, tzinfo=UTC)  # 11:00 em Manaus


@pytest.fixture
def qld(sessao, criar_usuario, monkeypatch):
    monkeypatch.setattr(tempo, "agora", lambda: AGORA)
    u = {
        "adm": criar_usuario("ADM-0001", Perfil.ADMINISTRADOR, nome="Ana"),
        "ges": criar_usuario("GES-0001", Perfil.SUPERVISOR, nome="Orlando"),
        "qua": criar_usuario("QUA-0001", Perfil.INSPETOR, nome="Maria"),
        "ope": criar_usuario("OPE-0001", Perfil.OPERADOR, nome="João"),
        "alm": criar_usuario("ALM-0001", Perfil.ALMOXARIFE, nome="Carlos"),
        "tec": criar_usuario("TEC-2001", Perfil.TECNICO, nome="João Lima"),
    }
    maquinas = [Equipamento(codigo_tag="TEST-02", nome="Testador FCT", setor="Testes Funcionais"),
                Equipamento(codigo_tag="SMT-01", nome="Insersora", setor="SMT")]
    produtos = [Produto(numero_serie="AMT-000017", modelo="AMT N16"), Produto(numero_serie="AMT-000018", modelo="AMT N17"),
                Produto(numero_serie="AMT-000099", modelo="AMT N14", ativo=False)]
    estacoes = [Estacao(nome="Teste Funcional"), Estacao(nome="SMT")]
    tipos = [TipoDefeito(nome="Tela"), TipoDefeito(nome="Teclado")]
    sessao.add_all(maquinas + produtos + estacoes + tipos)
    sessao.commit()
    return {"u": u, "maq": [m.id for m in maquinas], "prod": [p.id for p in produtos],
            "est": [e.id for e in estacoes], "tipo": [t.id for t in tipos]}


def corpo(q, **extra):
    base = {
        "ocorrida_em": "2026-11-12T08:30:00",  # sem fuso: hora de Manaus
        "classificacao": "MAIOR",
        "situacao_produto": "REPROVADO",
        "status": "ABERTA",
        "observacao": "Tela com linhas verticais no teste.",
        "acao_realizada": "Produto retido para reprocesso.",
        "produto_id": q["prod"][0],
        "estacao_id": q["est"][0],
        "tipo_defeito_id": q["tipo"][0],
        "equipamento_id": q["maq"][0],
    }
    return {**base, **extra}


def registrar(cliente, h, q, **extra):
    return cliente.post("/api/qld/ocorrencias", headers=h, json=corpo(q, **extra))


# ---------------------------------------------------------------- permissões


def test_permissoes_por_persona(cliente, token_de, qld):
    esperado = {
        "ADM-0001": dict(registrar=True, ocultar=True, cadastros=True),
        "GES-0001": dict(registrar=True, ocultar=True, cadastros=True),
        "QUA-0001": dict(registrar=True, ocultar=True, cadastros=False),
        "OPE-0001": dict(registrar=True, ocultar=False, cadastros=False),
        "ALM-0001": dict(registrar=False, ocultar=False, cadastros=False),
    }
    for matricula, perm in esperado.items():
        r = cliente.get("/api/qld/opcoes", headers=token_de(matricula))
        assert r.status_code == 200
        p = r.json()["permissoes"]
        assert {k: p[k] for k in perm} == perm, matricula
        assert p["editar"] == p["abrir_chamado"] == perm["registrar"]
    assert cliente.get("/api/qld/opcoes", headers=token_de("TEC-2001")).status_code == 403  # sem acesso ao módulo


def test_almoxarife_so_consulta(cliente, token_de, qld):
    h = token_de("ALM-0001")
    assert cliente.get("/api/qld/ocorrencias", headers=h).status_code == 200
    assert cliente.get("/api/qld/indicadores", headers=h).status_code == 200
    assert registrar(cliente, h, qld).status_code == 403


def test_operador_registra_mas_nao_oculta(cliente, token_de, qld):
    h = token_de("OPE-0001")
    r = registrar(cliente, h, qld)
    assert r.status_code == 201, r.text
    assert cliente.post(f"/api/qld/ocorrencias/{r.json()['ocorrencia']['id']}/ocultar", headers=h).status_code == 403


# ---------------------------------------------------------------- registro e edição


def test_registro_grava_responsavel_logado_e_hora_de_manaus_em_utc(cliente, token_de, qld, sessao):
    r = registrar(cliente, token_de("QUA-0001"), qld)
    assert r.status_code == 201, r.text
    oc = r.json()["ocorrencia"]
    assert oc["responsavel_nome"] == "Maria"
    assert oc["numero_serie"] == "AMT-000017" and oc["equipamento_tag"] == "TEST-02"
    assert datetime.fromisoformat(oc["ocorrida_em"]) == datetime(2026, 11, 12, 12, 30, tzinfo=UTC)
    assert oc["chamado_id"] is None
    # Sem produção na Rastreabilidade com esse número de série: só avisa.
    assert [a["tipo"] for a in r.json()["avisos"]] == ["aviso"]
    assert "não está em produção" in r.json()["avisos"][0]["mensagem"]


@pytest.mark.parametrize(
    ("extra", "trecho"),
    [
        ({"ocorrida_em": "2026-11-13T08:00:00"}, "futuro"),
        ({"observacao": "   "}, "observação"),
        ({"produto_id": 9999}, "Produto"),
    ],
)
def test_registro_invalido(cliente, token_de, qld, extra, trecho):
    r = registrar(cliente, token_de("QUA-0001"), qld, **extra)
    assert r.status_code == 422
    assert trecho in r.text


def test_produto_inativo_nao_entra_em_registro_novo(cliente, token_de, qld):
    r = registrar(cliente, token_de("QUA-0001"), qld, produto_id=qld["prod"][2])
    assert r.status_code == 422 and "inativo" in r.text


def test_edicao_mantem_responsavel_e_aceita_referencia_inativada_depois(cliente, token_de, qld, sessao):
    oc_id = registrar(cliente, token_de("OPE-0001"), qld).json()["ocorrencia"]["id"]
    sessao.get(Produto, qld["prod"][0]).ativo = False
    sessao.commit()

    r = cliente.put(f"/api/qld/ocorrencias/{oc_id}", headers=token_de("QUA-0001"),
                    json=corpo(qld, status="RESOLVIDA", acao_realizada="Tela substituída."))
    assert r.status_code == 200, r.text
    assert r.json()["responsavel_nome"] == "João"  # quem registrou, não quem editou
    assert r.json()["status"] == "RESOLVIDA"


def test_ocultar_tira_da_lista_e_dos_indicadores(cliente, token_de, qld):
    h = token_de("QUA-0001")
    a = registrar(cliente, h, qld).json()["ocorrencia"]["id"]
    b = registrar(cliente, h, qld, produto_id=qld["prod"][1]).json()["ocorrencia"]["id"]

    assert cliente.post(f"/api/qld/ocorrencias/{a}/ocultar", headers=h).status_code == 204
    assert [o["id"] for o in cliente.get("/api/qld/ocorrencias", headers=h).json()] == [b]
    assert cliente.get(f"/api/qld/ocorrencias/{a}", headers=h).status_code == 404
    assert cliente.post(f"/api/qld/ocorrencias/{a}/ocultar", headers=h).status_code == 404
    assert cliente.get("/api/qld/indicadores", headers=h).json()["total_ocorrencias"] == 1


# ---------------------------------------------------------------- integração com a Manutenção


def test_abrir_chamado_na_manutencao(cliente, token_de, qld, sessao):
    r = registrar(cliente, token_de("QUA-0001"), qld, classificacao="CRITICO", abrir_chamado=True)
    assert r.status_code == 201, r.text
    oc = r.json()["ocorrencia"]
    assert r.json()["avisos"][-1]["tipo"] == "sucesso"
    assert oc["chamado_id"] is not None and oc["chamado_status"] == "ABERTO"

    sessao.expire_all()
    chamado = sessao.get(Chamado, oc["chamado_id"])
    assert chamado.prioridade == "CRITICA"
    assert (chamado.origem_sistema, chamado.id_externo) == ("qualidade", f"QLD-{oc['id']}")
    assert chamado.operador_abertura_id == qld["u"]["qua"].id
    assert sessao.get(Equipamento, qld["maq"][0]).status_operacional == "PARADA"

    # Pedir de novo não duplica.
    r2 = cliente.post(f"/api/qld/ocorrencias/{oc['id']}/chamado", headers=token_de("QUA-0001"))
    assert r2.status_code == 200 and "já estava aberto" in r2.json()["avisos"][0]["mensagem"]
    assert len(sessao.scalars(select(Chamado)).all()) == 1


def test_maquina_ja_parada_vira_aviso_e_a_ocorrencia_fica_gravada(cliente, token_de, qld, sessao):
    h = token_de("QUA-0001")
    registrar(cliente, h, qld, abrir_chamado=True)
    r = registrar(cliente, h, qld, produto_id=qld["prod"][1], abrir_chamado=True)

    assert r.status_code == 201, r.text
    aviso = r.json()["avisos"][-1]
    assert aviso["tipo"] == "aviso" and "RN02" in aviso["mensagem"]
    assert r.json()["ocorrencia"]["chamado_id"] is None
    sessao.expire_all()
    assert len(sessao.scalars(select(Ocorrencia)).all()) == 2
    assert len(sessao.scalars(select(Chamado)).all()) == 1


def test_almoxarife_nao_abre_chamado_depois(cliente, token_de, qld):
    oc_id = registrar(cliente, token_de("QUA-0001"), qld).json()["ocorrencia"]["id"]
    assert cliente.post(f"/api/qld/ocorrencias/{oc_id}/chamado", headers=token_de("ALM-0001")).status_code == 403


# ---------------------------------------------------------------- consulta e indicadores


def test_filtros_busca_e_dia_da_fabrica(cliente, token_de, qld):
    h = token_de("QUA-0001")
    # 23:30 de 11/11 em Manaus = 03:30 UTC de 12/11: conta no dia 11 da fábrica.
    noite = registrar(cliente, h, qld, ocorrida_em="2026-11-11T23:30:00-04:00", classificacao="MENOR").json()["ocorrencia"]
    manha = registrar(cliente, h, qld, produto_id=qld["prod"][1], tipo_defeito_id=qld["tipo"][1]).json()["ocorrencia"]

    def ids(**params):
        return [o["id"] for o in cliente.get("/api/qld/ocorrencias", headers=h, params=params).json()]

    assert ids() == [manha["id"], noite["id"]]  # mais recente primeiro
    assert ids(de="2026-11-11", ate="2026-11-11") == [noite["id"]]
    assert ids(de="2026-11-12") == [manha["id"]]
    assert ids(busca="000018") == [manha["id"]]
    assert ids(busca="teclado") == [manha["id"]]
    assert ids(busca=f"#{noite['id']}") == [noite["id"]]
    assert ids(classificacao="MENOR") == [noite["id"]]
    assert ids(tipo_defeito_id=qld["tipo"][1]) == [manha["id"]]


def test_indicadores(cliente, token_de, qld):
    h = token_de("QUA-0001")
    registrar(cliente, h, qld, ocorrida_em="2026-11-11T23:30:00-04:00")
    registrar(cliente, h, qld, situacao_produto="REPROVADO", status="RESOLVIDA")  # mesmo produto: conta 1 vez
    registrar(cliente, h, qld, produto_id=qld["prod"][1], estacao_id=qld["est"][1], situacao_produto="APROVADO",
              classificacao="CRITICO", status="EM_ANALISE")

    i = cliente.get("/api/qld/indicadores", headers=h).json()
    assert i["total_ocorrencias"] == 3
    assert i["ocorrencias_abertas"] == 1 and i["ocorrencias_em_analise"] == 1
    assert i["produtos_reprovados"] == 1
    assert i["criticas"] == 1
    assert i["estacao_critica"] == "Teste Funcional"
    assert i["por_estacao"] == [{"rotulo": "Teste Funcional", "ocorrencias": 2}, {"rotulo": "SMT", "ocorrencias": 1}]
    assert i["por_dia"] == [{"data": "2026-11-11", "ocorrencias": 1}, {"data": "2026-11-12", "ocorrencias": 2}]

    so_dia_11 = cliente.get("/api/qld/indicadores", headers=h, params={"de": "2026-11-11", "ate": "2026-11-11"}).json()
    assert so_dia_11["total_ocorrencias"] == 1


# ---------------------------------------------------------------- cadastros


def test_cadastros(cliente, token_de, qld):
    h = token_de("GES-0001")
    # Notebooks vêm da Rastreabilidade: a lista de produtos da Qualidade é só consulta.
    assert cliente.post("/api/qld/produtos", headers=h, json={"numero_serie": "AMT-000031", "modelo": "X"}).status_code == 405
    assert cliente.post("/api/qld/estacoes", headers=h, json={"nome": "smt"}).status_code == 409  # sem diferenciar maiúsculas

    tipo = cliente.post("/api/qld/tipos-defeito", headers=h, json={"nome": "Bateria", "descricao": "Não carrega"}).json()
    assert cliente.patch(f"/api/qld/tipos-defeito/{tipo['id']}", headers=h, json={"ativo": False}).json()["ativo"] is False
    nomes = [t["nome"] for t in cliente.get("/api/qld/tipos-defeito", headers=h).json()]
    assert "Bateria" not in nomes
    todos = cliente.get("/api/qld/tipos-defeito", headers=h, params={"incluir_inativos": True}).json()
    assert "Bateria" in [t["nome"] for t in todos]

    assert cliente.post("/api/qld/estacoes", headers=token_de("QUA-0001"), json={"nome": "Nova"}).status_code == 403


def test_maquinas_vem_da_manutencao(cliente, token_de, qld, sessao):
    sessao.get(Equipamento, qld["maq"][1]).ativo = False
    sessao.commit()
    r = cliente.get("/api/qld/maquinas", headers=token_de("ALM-0001"))
    assert [m["codigo_tag"] for m in r.json()] == ["TEST-02"]


# ---------------------------------------------------------------- notebooks da Rastreabilidade


@pytest.fixture
def producoes(sessao, qld):
    """Produções na Rastreabilidade: AMT-000031 (nova, Em Teste), AMT-000017 (já tem produto na Qualidade, sem
    ligação) e AMT-000040 (expedida)."""
    etapas = {n: Etapa(nome=n, ordem=o) for n, o in ETAPAS_PADRAO}
    modelo = Modelo(codigo="N18-I7-16-512", nome="AMT N18")
    sessao.add_all([*etapas.values(), modelo])
    sessao.commit()
    criador = qld["u"]["ope"].id

    def nova(serie: str, etapa: str, minutos: int) -> Producao:
        quando = AGORA - timedelta(minutes=minutos)
        return Producao(numero_serie=serie, id_unica=f"PRD-{serie}", modelo_id=modelo.id, etapa_id=etapas[etapa].id,
                        responsavel_id=criador, criado_por_id=criador, iniciada_em=quando, atualizada_em=quando)

    lista = [nova("AMT-000031", "Em Teste", 5), nova("AMT-000017", "Em Teste", 30), nova("AMT-000040", "Expedição", 60)]
    sessao.add_all(lista)
    sessao.commit()
    return {p.numero_serie: p.id for p in lista}


def test_lista_de_notebooks_vem_da_rastreabilidade(cliente, token_de, qld, producoes):
    h = token_de("QUA-0001")
    r = cliente.get("/api/qld/notebooks", headers=h)
    assert r.status_code == 200
    assert [n["numero_serie"] for n in r.json()] == ["AMT-000031", "AMT-000017"]  # expedido fica de fora
    assert r.json()[0] == {"id": producoes["AMT-000031"], "numero_serie": "AMT-000031", "modelo": "AMT N18", "etapa": "Em Teste"}
    assert [n["numero_serie"] for n in cliente.get("/api/qld/notebooks", headers=h, params={"busca": "017"}).json()] == ["AMT-000017"]


def test_notebook_novo_recebe_ocorrencia_pela_producao(cliente, token_de, qld, producoes, sessao):
    h = token_de("QUA-0001")
    r = registrar(cliente, h, qld, produto_id=None, producao_id=producoes["AMT-000031"], situacao_produto="REPROVADO")
    assert r.status_code == 201, r.text
    oc = r.json()["ocorrencia"]
    assert (oc["numero_serie"], oc["modelo"], oc["producao_id"]) == ("AMT-000031", "AMT N18", producoes["AMT-000031"])
    # A Rastreabilidade foi atualizada pela ligação: nada de "não está em produção".
    assert r.json()["avisos"][0]["tipo"] == "sucesso"
    sessao.expire_all()
    assert sessao.get(Producao, producoes["AMT-000031"]).etapa.nome == "Reprovado"

    # Segunda ocorrência do mesmo notebook reaproveita o mesmo produto.
    r2 = registrar(cliente, h, qld, produto_id=None, producao_id=producoes["AMT-000031"], situacao_produto="APROVADO")
    assert r2.json()["ocorrencia"]["produto_id"] == oc["produto_id"]
    assert len(sessao.scalars(select(Produto).where(Produto.numero_serie == "AMT-000031")).all()) == 1


def test_produto_do_historico_e_ligado_sem_duplicar(cliente, token_de, qld, producoes, sessao):
    r = registrar(cliente, token_de("QUA-0001"), qld, produto_id=None, producao_id=producoes["AMT-000017"])
    assert r.status_code == 201, r.text
    assert r.json()["ocorrencia"]["produto_id"] == qld["prod"][0]  # o AMT-000017 que já existia
    sessao.expire_all()
    produto = sessao.get(Produto, qld["prod"][0])
    assert (produto.producao_id, produto.modelo) == (producoes["AMT-000017"], "AMT N18")  # modelo da Rastreabilidade


def test_notebook_expedido_e_escolha_obrigatoria(cliente, token_de, qld, producoes):
    h = token_de("QUA-0001")
    r = registrar(cliente, h, qld, produto_id=None, producao_id=producoes["AMT-000040"])
    assert r.status_code == 422 and "expedido" in r.text
    r = registrar(cliente, h, qld, produto_id=None, producao_id=99999)
    assert r.status_code == 422 and "Rastreabilidade" in r.text
    r = registrar(cliente, h, qld, produto_id=None)
    assert r.status_code == 422 and "Escolha o notebook" in r.text


def test_vincular_produtos_por_serie(qld, producoes, sessao):
    from app.modulos.qualidade import servico

    assert servico.vincular_produtos_por_serie(sessao) == 1  # só o AMT-000017 tem produção
    assert servico.vincular_produtos_por_serie(sessao) == 0  # de novo: nada a fazer
    assert sessao.get(Produto, qld["prod"][1]).producao_id is None  # AMT-000018: histórico
