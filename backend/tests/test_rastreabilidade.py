"""Testes do módulo de Rastreabilidade (/api/ras).

Portam as regras de rastreabilidade/tests (número de série, etapas, reprovação com não conformidade, fluxo de
materiais com estoque, máquinas por chave) e cobrem as permissões por persona e o elo com a Qualidade.
"""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core import tempo
from app.core.rbac import Perfil
from app.modulos.manutencao.modelos import Equipamento
from app.modulos.qualidade.modelos import Estacao, Produto, TipoDefeito
from app.modulos.rastreabilidade.constantes import ETAPAS_PADRAO
from app.modulos.rastreabilidade.modelos import Componente, Etapa, Modelo, ModeloComponente, NaoConformidade, Passagem

AGORA = datetime(2026, 11, 12, 2, 30, tzinfo=UTC)  # 22:30 de 11/11 em Manaus
CHAVE = {"X-API-Key": "amatech-iot-demo"}


@pytest.fixture
def ras(sessao, criar_usuario, monkeypatch):
    monkeypatch.setattr(tempo, "agora", lambda: AGORA)
    u = {
        "adm": criar_usuario("ADM-0001", Perfil.ADMINISTRADOR, nome="Ana"),
        "ges": criar_usuario("GES-0001", Perfil.SUPERVISOR, nome="Orlando"),
        "ope": criar_usuario("OPE-0001", Perfil.OPERADOR, nome="João"),
        "qua": criar_usuario("QUA-0001", Perfil.INSPETOR, nome="Maria"),
        "alm": criar_usuario("ALM-0001", Perfil.ALMOXARIFE, nome="Carlos"),
        "tec": criar_usuario("TEC-2001", Perfil.TECNICO, nome="João Lima"),
        "svc": criar_usuario("SVC-INTEGRACAO", Perfil.OPERADOR, ativo=False, nome="Integração"),
    }
    etapas = {nome: Etapa(nome=nome, ordem=ordem) for nome, ordem in ETAPAS_PADRAO}
    cpu = Componente(sku="CPU-I5-12", nome="Processador i5", estoque=10)
    ram = Componente(sku="RAM-8G-D4", nome="Memória 8GB", estoque=3)
    modelo = Modelo(codigo="N14-I5-8-256", nome="AMT N14", meta=600)
    modelo.componentes = [ModeloComponente(componente=cpu, quantidade=1), ModeloComponente(componente=ram, quantidade=2)]
    sessao.add_all([*etapas.values(), cpu, ram, modelo])
    sessao.commit()
    return {"u": u, "etapa": {n: e.id for n, e in etapas.items()}, "cpu": cpu.id, "ram": ram.id, "modelo": modelo.id}


def nova_producao(cliente, h, ras, **extra):
    r = cliente.post("/api/ras/producoes", headers=h, json={"modelo_id": ras["modelo"], **extra})
    assert r.status_code == 201, r.text
    return r.json()


def mudar(cliente, h, producao_id, etapa_id, **extra):
    return cliente.post(f"/api/ras/producoes/{producao_id}/etapa", headers=h, json={"etapa_id": etapa_id, **extra})


# ---------------------------------------------------------------- permissões


def test_permissoes_por_persona(cliente, token_de, ras):
    esperado = {
        "ADM-0001": dict(producao=True, excluir_producao=True, solicitar=True, baixar=True, componentes=True, modelos_etapas=True),
        "GES-0001": dict(producao=True, excluir_producao=True, solicitar=True, baixar=False, componentes=True, modelos_etapas=True),
        "OPE-0001": dict(producao=True, excluir_producao=False, solicitar=True, baixar=False, componentes=False, modelos_etapas=False),
        "QUA-0001": dict(producao=True, excluir_producao=False, solicitar=False, baixar=False, componentes=False, modelos_etapas=False),
        "ALM-0001": dict(producao=False, excluir_producao=False, solicitar=True, baixar=True, componentes=True, modelos_etapas=False),
    }
    for matricula, perm in esperado.items():
        r = cliente.get("/api/ras/opcoes", headers=token_de(matricula))
        assert r.status_code == 200 and r.json()["permissoes"] == perm, matricula
    responsaveis = [p["matricula"] for p in cliente.get("/api/ras/opcoes", headers=token_de("ADM-0001")).json()["responsaveis"]]
    assert "TEC-2001" not in responsaveis and "SVC-INTEGRACAO" not in responsaveis  # sem acesso / inativo
    assert cliente.get("/api/ras/producoes", headers=token_de("TEC-2001")).status_code == 403


# ---------------------------------------------------------------- produção


def test_criar_producao_gera_serie_id_unica_e_primeira_passagem(cliente, token_de, ras, sessao):
    p = nova_producao(cliente, token_de("OPE-0001"), ras)
    assert p["numero_serie"] == f"AMT-{p['id']:06d}"
    assert p["id_unica"] == f"PRD-{p['numero_serie']}-20261111"  # dia da fábrica, não o dia UTC
    assert p["etapa_nome"] == "Em Fila" and p["responsavel_nome"] == "João"
    assert [h["etapa_nome"] for h in p["passagens"]] == ["Em Fila"]
    assert p["proxima_etapa_id"] == ras["etapa"]["Em Montagem"]


def test_almoxarife_nao_cria_producao(cliente, token_de, ras):
    r = cliente.post("/api/ras/producoes", headers=token_de("ALM-0001"), json={"modelo_id": ras["modelo"]})
    assert r.status_code == 403


def test_mudar_etapa_registra_passagem_e_reprovar_exige_falha(cliente, token_de, ras, sessao):
    h = token_de("QUA-0001")
    p = nova_producao(cliente, token_de("OPE-0001"), ras)
    e = ras["etapa"]

    r = mudar(cliente, h, p["id"], e["Em Montagem"], responsavel_id=ras["u"]["ope"].id)
    assert r.status_code == 200 and r.json()["etapa_nome"] == "Em Montagem"
    assert mudar(cliente, h, p["id"], e["Em Montagem"]).status_code == 409  # já está nessa etapa

    sem_falha = mudar(cliente, h, p["id"], e["Reprovado"])
    assert sem_falha.status_code == 422 and "falha" in sem_falha.text

    r = mudar(cliente, h, p["id"], e["Reprovado"], descricao_falha="Tela com pixels mortos", motivo_reprovacao="Defeito de tela")
    d = r.json()
    assert d["etapa_nome"] == "Reprovado"
    assert [x["etapa_nome"] for x in d["passagens"]] == ["Em Fila", "Em Montagem", "Reprovado"]
    assert d["passagens"][-1]["usuario_nome"] == "Maria"
    assert d["nao_conformidades"][0]["motivo_reprovacao"] == "Defeito de tela"
    assert d["proxima_etapa_id"] == e["Em Montagem"]  # de Reprovado volta para a 2ª etapa (retrabalho)


def test_nao_conformidade_sem_mudar_etapa(cliente, token_de, ras):
    p = nova_producao(cliente, token_de("OPE-0001"), ras)
    r = cliente.post(f"/api/ras/producoes/{p['id']}/nao-conformidades", headers=token_de("QUA-0001"),
                     json={"descricao_falha": "Risco na tampa", "motivo_reprovacao": "Estético"})
    assert r.status_code == 201
    assert r.json()["etapa_nome"] == "Em Fila" and len(r.json()["nao_conformidades"]) == 1


def test_busca_e_filtros(cliente, token_de, ras):
    h = token_de("OPE-0001")
    a = nova_producao(cliente, h, ras)
    b = nova_producao(cliente, h, ras)
    mudar(cliente, h, b["id"], ras["etapa"]["Em Montagem"])

    def series(**params):
        return [p["numero_serie"] for p in cliente.get("/api/ras/producoes", headers=h, params=params).json()]

    assert series(busca=a["numero_serie"][-3:]) == [a["numero_serie"]]
    assert series(busca="n14") == [b["numero_serie"], a["numero_serie"]]  # atualizada por último primeiro
    assert series(etapa_id=ras["etapa"]["Em Montagem"]) == [b["numero_serie"]]


def test_excluir_producao(cliente, token_de, ras):
    p = nova_producao(cliente, token_de("OPE-0001"), ras)
    assert cliente.delete(f"/api/ras/producoes/{p['id']}", headers=token_de("OPE-0001")).status_code == 403

    cliente.post(f"/api/ras/producoes/{p['id']}/solicitar-materiais", headers=token_de("OPE-0001"))
    sol = cliente.get("/api/ras/solicitacoes", headers=token_de("ALM-0001")).json()[0]
    cliente.post("/api/ras/baixas", headers=token_de("ALM-0001"), json={"solicitacao_id": sol["id"], "quantidade": 1})
    r = cliente.delete(f"/api/ras/producoes/{p['id']}", headers=token_de("GES-0001"))
    assert r.status_code == 409 and "baixas" in r.text

    outra = nova_producao(cliente, token_de("OPE-0001"), ras)
    assert cliente.delete(f"/api/ras/producoes/{outra['id']}", headers=token_de("GES-0001")).status_code == 204
    assert cliente.get(f"/api/ras/producoes/{outra['id']}", headers=token_de("GES-0001")).status_code == 404


# ---------------------------------------------------------------- materiais


def test_fluxo_de_materiais_com_estoque(cliente, token_de, ras, sessao):
    ope, alm = token_de("OPE-0001"), token_de("ALM-0001")
    p = nova_producao(cliente, ope, ras)

    r = cliente.post(f"/api/ras/producoes/{p['id']}/solicitar-materiais", headers=ope)
    assert r.json() == {"criadas": 2, "ignoradas": 0}
    assert cliente.post(f"/api/ras/producoes/{p['id']}/solicitar-materiais", headers=ope).json() == {"criadas": 0, "ignoradas": 2}

    sols = {s["sku"]: s for s in cliente.get("/api/ras/solicitacoes", headers=alm, params={"producao_id": p["id"]}).json()}
    ram = sols["RAM-8G-D4"]
    assert ram["quantidade"] == 2 and ram["status"] == "PENDENTE"

    assert cliente.post("/api/ras/baixas", headers=ope, json={"solicitacao_id": ram["id"], "quantidade": 1}).status_code == 403
    b = cliente.post("/api/ras/baixas", headers=alm, json={"solicitacao_id": ram["id"], "quantidade": 1})
    assert b.status_code == 201, b.text
    s = cliente.get("/api/ras/solicitacoes", headers=alm, params={"status": "PARCIAL"}).json()
    assert [x["id"] for x in s] == [ram["id"]] and s[0]["estoque"] == 2

    excede = cliente.post("/api/ras/baixas", headers=alm, json={"solicitacao_id": ram["id"], "quantidade": 2})
    assert excede.status_code == 409 and "saldo" in excede.text

    cliente.post("/api/ras/baixas", headers=alm, json={"solicitacao_id": ram["id"], "quantidade": 1})
    atendida = cliente.get("/api/ras/solicitacoes", headers=alm, params={"status": "ATENDIDA"}).json()
    assert [x["id"] for x in atendida] == [ram["id"]]

    # Alterar a baixa devolve a diferença; excluir devolve tudo e a solicitação volta a ter pendência.
    bid = b.json()["id"]
    assert cliente.put(f"/api/ras/baixas/{bid}", headers=alm, json={"quantidade": 3}).status_code == 409  # passa do saldo
    assert cliente.delete(f"/api/ras/baixas/{bid}", headers=alm).status_code == 204
    sessao.expire_all()
    assert sessao.get(Componente, ras["ram"]).estoque == 2
    assert cliente.get("/api/ras/solicitacoes", headers=alm, params={"status": "PARCIAL"}).json()[0]["id"] == ram["id"]

    excluir = cliente.delete(f"/api/ras/solicitacoes/{ram['id']}", headers=ope)
    assert excluir.status_code == 409  # ainda tem uma baixa


def test_baixa_maior_que_estoque_e_solicitacao_cancelada(cliente, token_de, ras):
    ope, alm = token_de("OPE-0001"), token_de("ALM-0001")
    p = nova_producao(cliente, ope, ras)
    s = cliente.post("/api/ras/solicitacoes", headers=ope,
                     json={"producao_id": p["id"], "componente_id": ras["ram"], "quantidade": 5}).json()
    r = cliente.post("/api/ras/baixas", headers=alm, json={"solicitacao_id": s["id"], "quantidade": 4})
    assert r.status_code == 409 and "Estoque insuficiente" in r.text

    c = cliente.put(f"/api/ras/solicitacoes/{s['id']}", headers=ope, json={"quantidade": 5, "cancelada": True})
    assert c.json()["status"] == "CANCELADA"
    r = cliente.post("/api/ras/baixas", headers=alm, json={"solicitacao_id": s["id"], "quantidade": 1})
    assert r.status_code == 409 and "cancelada" in r.text


# ---------------------------------------------------------------- máquinas


def test_maquina_informa_etapa_com_chave(cliente, token_de, ras, sessao):
    p = nova_producao(cliente, token_de("OPE-0001"), ras)
    corpo = {"numero_serie": p["numero_serie"].lower(), "etapa": "em teste", "maquina": "TEST-01"}
    assert cliente.post("/api/ras/maquinas/status", json=corpo).status_code == 401
    assert cliente.post("/api/ras/maquinas/status", json=corpo, headers={"X-API-Key": "errada"}).status_code == 401

    r = cliente.post("/api/ras/maquinas/status", json=corpo, headers=CHAVE)
    assert r.status_code == 200 and r.json()["alterado"] is True and r.json()["producao"]["etapa_nome"] == "Em Teste"
    assert cliente.post("/api/ras/maquinas/status", json=corpo, headers=CHAVE).json()["alterado"] is False

    r = cliente.post("/api/ras/maquinas/status", json={**corpo, "etapa": "Reprovado"}, headers=CHAVE)
    sessao.expire_all()
    nc = sessao.scalar(select(NaoConformidade))
    assert "TEST-01" in nc.descricao_falha and nc.usuario_id == ras["u"]["svc"].id
    origens = sessao.scalars(select(Passagem.origem).where(Passagem.producao_id == p["id"]).order_by(Passagem.id)).all()
    assert origens == ["MANUAL", "MAQUINA/IOT", "MAQUINA/IOT"]

    assert cliente.post("/api/ras/maquinas/status", json={**corpo, "numero_serie": "AMT-999999"}, headers=CHAVE).status_code == 404
    assert cliente.post("/api/ras/maquinas/status", json={**corpo, "etapa": "Voando"}, headers=CHAVE).status_code == 404


# ---------------------------------------------------------------- Qualidade -> Rastreabilidade


@pytest.fixture
def inspecao(sessao, ras):
    """Cadastros da Qualidade para registrar ocorrências do notebook criado no teste."""
    maquina = Equipamento(codigo_tag="TEST-02", nome="Testador", setor="Testes")
    estacao, tipo = Estacao(nome="Teste Funcional"), TipoDefeito(nome="Tela")
    sessao.add_all([maquina, estacao, tipo])
    sessao.commit()

    def registrar(cliente, numero_serie, situacao, classificacao="MAIOR"):
        produto = sessao.scalar(select(Produto).where(Produto.numero_serie == numero_serie))
        if produto is None:
            produto = Produto(numero_serie=numero_serie, modelo="AMT N14")
            sessao.add(produto)
            sessao.commit()
        from tests.conftest import SENHA  # noqa: PLC0415
        tok = cliente.post("/api/auth/login", json={"matricula": "QUA-0001", "senha": SENHA}).json()["access_token"]
        r = cliente.post("/api/qld/ocorrencias", headers={"Authorization": f"Bearer {tok}"}, json={
            "ocorrida_em": "2026-11-11T20:00:00", "classificacao": classificacao, "situacao_produto": situacao,
            "status": "ABERTA", "observacao": "Linhas na tela", "acao_realizada": "Retido", "produto_id": produto.id,
            "estacao_id": estacao.id, "tipo_defeito_id": tipo.id, "equipamento_id": maquina.id,
        })
        assert r.status_code == 201, r.text
        return r.json()

    return registrar


def _etapas(cliente, h, producao_id):
    return [x["etapa_nome"] for x in cliente.get(f"/api/ras/producoes/{producao_id}", headers=h).json()["passagens"]]


def test_qualidade_reprova_e_reprocessa(cliente, token_de, ras, inspecao):
    h = token_de("ADM-0001")
    p = nova_producao(cliente, h, ras)
    mudar(cliente, h, p["id"], ras["etapa"]["Em Teste"])

    r = inspecao(cliente, p["numero_serie"], "REPROVADO")
    assert "marcado como Reprovado" in r["avisos"][0]["mensagem"]
    d = cliente.get(f"/api/ras/producoes/{p['id']}", headers=h).json()
    assert d["etapa_nome"] == "Reprovado"
    nc = d["nao_conformidades"][0]
    assert (nc["origem_sistema"], nc["id_externo"]) == ("qualidade", f"QLD-{r['ocorrencia']['id']}")
    assert nc["motivo_reprovacao"] == "Tela (Maior)"
    assert d["passagens"][-1]["origem"] == "QUALIDADE"

    outro = nova_producao(cliente, h, ras)
    inspecao(cliente, outro["numero_serie"], "EM_REPROCESSO")
    assert _etapas(cliente, h, outro["id"]) == ["Em Fila", "Reprovado", "Em Montagem"]


def test_qualidade_reprova_notebook_ja_reprovado_grava_a_nao_conformidade(cliente, token_de, ras, inspecao):
    h = token_de("ADM-0001")
    p = nova_producao(cliente, h, ras)
    mudar(cliente, h, p["id"], ras["etapa"]["Reprovado"], descricao_falha="Teclado", motivo_reprovacao="Falha no teclado")

    r = inspecao(cliente, p["numero_serie"], "REPROVADO")
    assert "já estava Reprovado; não conformidade registrada" in r["avisos"][0]["mensagem"]
    d = cliente.get(f"/api/ras/producoes/{p['id']}", headers=h).json()
    assert [x["etapa_nome"] for x in d["passagens"]] == ["Em Fila", "Reprovado"]  # sem passagem repetida
    assert [(n["origem_sistema"], n["motivo_reprovacao"]) for n in d["nao_conformidades"]] == [
        (None, "Falha no teclado"), ("qualidade", "Tela (Maior)")]

    # Em reprocesso a partir de Reprovado: grava a NC e devolve para a montagem.
    outra = inspecao(cliente, p["numero_serie"], "EM_REPROCESSO")
    assert "Em Montagem" in outra["avisos"][0]["mensagem"]
    assert _etapas(cliente, h, p["id"])[-1] == "Em Montagem"


def test_qualidade_aprova_sem_voltar_notebook_adiantado(cliente, token_de, ras, inspecao):
    h = token_de("ADM-0001")
    em_teste = nova_producao(cliente, h, ras)
    mudar(cliente, h, em_teste["id"], ras["etapa"]["Em Teste"])
    r = inspecao(cliente, em_teste["numero_serie"], "APROVADO")
    assert "marcado como Aprovado" in r["avisos"][0]["mensagem"]

    embalado = nova_producao(cliente, h, ras)
    mudar(cliente, h, embalado["id"], ras["etapa"]["Embalagem"])
    r = inspecao(cliente, embalado["numero_serie"], "APROVADO")
    assert "nada a alterar" in r["avisos"][0]["mensagem"]
    assert _etapas(cliente, h, embalado["id"])[-1] == "Embalagem"


# ---------------------------------------------------------------- cadastros, painel e relatórios


def test_cadastros_e_permissoes(cliente, token_de, ras):
    alm, ges = token_de("ALM-0001"), token_de("GES-0001")
    assert cliente.post("/api/ras/componentes", headers=alm, json={"sku": "ssd-256-nv", "nome": "SSD"}).json()["sku"] == "SSD-256-NV"
    assert cliente.post("/api/ras/componentes", headers=alm, json={"sku": "SSD-256-NV", "nome": "X"}).status_code == 409
    assert cliente.post("/api/ras/modelos", headers=alm, json={"codigo": "X", "nome": "X"}).status_code == 403

    m = cliente.post("/api/ras/modelos", headers=ges, json={
        "codigo": "n15-i5", "nome": "AMT N15", "componentes": [{"componente_id": ras["cpu"], "quantidade": 1}]}).json()
    assert m["codigo"] == "N15-I5" and [c["sku"] for c in m["componentes"]] == ["CPU-I5-12"]
    m = cliente.patch(f"/api/ras/modelos/{m['id']}", headers=ges, json={
        "componentes": [{"componente_id": ras["ram"], "quantidade": 2}]}).json()
    assert [(c["sku"], c["quantidade"]) for c in m["componentes"]] == [("RAM-8G-D4", 2)]
    duplicado = cliente.patch(f"/api/ras/modelos/{m['id']}", headers=ges, json={
        "componentes": [{"componente_id": ras["ram"], "quantidade": 1}, {"componente_id": ras["ram"], "quantidade": 2}]})
    assert duplicado.status_code == 422

    nova = cliente.post("/api/ras/etapas", headers=ges, json={"nome": "Gravação de BIOS"}).json()
    assert nova["ordem"] == 7  # depois da última etapa do fluxo principal (Expedição = 6)
    assert cliente.delete(f"/api/ras/etapas/{nova['id']}", headers=ges).status_code == 204
    assert cliente.delete(f"/api/ras/etapas/{ras['etapa']['Em Fila']}", headers=ges).status_code == 204  # nunca usada
    nova_producao(cliente, ges, ras)
    usada = cliente.delete(f"/api/ras/etapas/{ras['etapa']['Em Montagem']}", headers=ges)
    assert usada.status_code == 409  # a produção começou nela (primeira etapa agora)


def test_painel_e_relatorios(cliente, token_de, ras):
    h = token_de("ADM-0001")
    p = nova_producao(cliente, h, ras)
    mudar(cliente, h, p["id"], ras["etapa"]["Reprovado"], descricao_falha="Wi-Fi", motivo_reprovacao="Módulo")
    cliente.post(f"/api/ras/producoes/{p['id']}/solicitar-materiais", headers=h)

    painel = cliente.get("/api/ras/painel", headers=h).json()
    assert painel["kpis"]["iniciadas_hoje"] == 1 and painel["kpis"]["reprovados"] == 1
    assert painel["kpis"]["solicitacoes_pendentes"] == 2
    assert painel["kpis"]["estoque_critico"] == 2  # 10 e 3 unidades: abaixo do limite de 50
    assert painel["ultimos_dias"][-1] == {"data": "2026-11-11", "quantidade": 1}

    estoque = cliente.get("/api/ras/relatorios/estoque", headers=h).json()
    ram = next(l for l in estoque["linhas"] if l["sku"] == "RAM-8G-D4")
    assert (ram["pendente"], ram["saldo"], ram["situacao"]) == (2, 1, "CRÍTICO")

    ncs = cliente.get("/api/ras/relatorios/nao_conformidades", headers=h, params={"de": "2026-11-11", "ate": "2026-11-11"}).json()
    assert len(ncs["linhas"]) == 1 and ncs["colunas"][0] == {"chave": "data", "titulo": "Data", "formato": "data"}
    vazio = cliente.get("/api/ras/relatorios/producao", headers=h, params={"de": "2026-11-12"}).json()
    assert vazio["linhas"] == []
    assert cliente.get("/api/ras/relatorios/inexistente", headers=h).status_code == 404
