"""Testes do módulo de Manutenção (/api/mnt).

Portam as regras de manutencao/tests/test_management_control.py e test_integracao_ecossistema.py
(RN02 a RN09, auditoria, soft delete, abertura por outro módulo) e acrescentam as permissões por persona.
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.core import tempo
from app.core.rbac import Perfil
from app.modulos.manutencao import servico
from app.modulos.manutencao.constantes import Prioridade
from app.modulos.manutencao.modelos import Chamado, Equipamento, Peca

INICIO = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)  # 08:00 em Manaus


class Relogio:
    """Substitui tempo.agora() para os cálculos de downtime/MTTR serem exatos."""

    def __init__(self, inicio: datetime):
        self.atual = inicio

    def __call__(self) -> datetime:
        return self.atual

    def avancar(self, minutos: int) -> None:
        self.atual += timedelta(minutes=minutos)


@pytest.fixture
def relogio(monkeypatch) -> Relogio:
    r = Relogio(INICIO)
    monkeypatch.setattr(tempo, "agora", r)
    return r


@pytest.fixture
def fabrica(sessao, criar_usuario):
    """Personas + 3 máquinas + 2 peças (uma inativa)."""
    usuarios = {
        "adm": criar_usuario("ADM-0001", Perfil.ADMINISTRADOR, nome="Ana"),
        "ges": criar_usuario("GES-0001", Perfil.SUPERVISOR, nome="Orlando"),
        "ope": criar_usuario("OPE-0001", Perfil.OPERADOR, nome="João"),
        "ope2": criar_usuario("OPE-0002", Perfil.OPERADOR, nome="Lucas"),
        "tec": criar_usuario("TEC-2001", Perfil.TECNICO, nome="João Lima"),
        "tec2": criar_usuario("TEC-2002", Perfil.TECNICO, nome="Mariana"),
        "qua": criar_usuario("QUA-0001", Perfil.INSPETOR, nome="Maria"),
        "alm": criar_usuario("ALM-0001", Perfil.ALMOXARIFE, nome="Carlos"),
    }
    maquinas = [
        Equipamento(codigo_tag="SMT-01", nome="Insersora", setor="SMT", posto_trabalho="Posto 01"),
        Equipamento(codigo_tag="TEST-01", nome="Testador ICT", setor="Testes Funcionais"),
        Equipamento(codigo_tag="QC-01", nome="Bancada de Inspeção", setor="Inspeção da Qualidade"),
    ]
    pecas = [
        Peca(codigo_peca="PN-SEN-030", nome="Sensor óptico", unidade_medida="UN"),
        Peca(codigo_peca="PN-OLD-001", nome="Peça descontinuada", unidade_medida="UN", ativo=False),
    ]
    sessao.add_all(maquinas + pecas)
    sessao.commit()
    return {"u": usuarios, "smt": maquinas[0].id, "test": maquinas[1].id, "qc": maquinas[2].id, "sensor": pecas[0].id, "velha": pecas[1].id}


def status_maquina(cliente, h, equipamento_id) -> str:
    return next(e for e in cliente.get("/api/mnt/equipamentos", headers=h).json() if e["id"] == equipamento_id)[
        "status_operacional"
    ]


def abrir(cliente, h, equipamento_id, prioridade="ALTA", descricao="Falha no bico de vácuo do cabeçote 2"):
    return cliente.post(
        "/api/mnt/chamados", headers=h, json={"equipamento_id": equipamento_id, "prioridade": prioridade, "descricao_falha": descricao}
    )


# ---------------------------------------------------------------- ciclo completo


def test_fluxo_completo_rn02_a_rn09(cliente, fabrica, token_de, relogio):
    ope, tec, tec2 = token_de("OPE-0001"), token_de("TEC-2001"), token_de("TEC-2002")
    smt = fabrica["smt"]

    # Abertura: máquina PARADA, chamado ABERTO
    r = abrir(cliente, ope, smt, prioridade="CRITICA")
    assert r.status_code == 201, r.text
    os_ = r.json()
    assert os_["status_chamado"] == "ABERTO" and os_["operador_nome"] == "João"
    assert status_maquina(cliente, ope, smt) == "PARADA"

    # RN02: segunda abertura na mesma máquina é bloqueada
    dup = abrir(cliente, token_de("OPE-0002"), smt)
    assert dup.status_code == 409 and "RN02" in dup.json()["detail"]

    # Fila: Crítica no topo, mesmo aberta depois de uma Alta
    relogio.avancar(1)
    abrir(cliente, ope, fabrica["test"], prioridade="ALTA")
    fila = cliente.get("/api/mnt/chamados/fila", headers=tec).json()
    assert [c["id"] for c in fila][0] == os_["id"]

    # Técnico assume 15 min depois da abertura: EM_ANDAMENTO / EM_MANUTENCAO
    relogio.avancar(14)
    r = cliente.post(f"/api/mnt/chamados/{os_['id']}/assumir", headers=tec)
    assert r.status_code == 200 and r.json()["tecnico_nome"] == "João Lima"
    assert status_maquina(cliente, tec, smt) == "EM_MANUTENCAO"
    # Assumir de novo: já não está ABERTO
    assert cliente.post(f"/api/mnt/chamados/{os_['id']}/assumir", headers=tec2).status_code == 409

    # RN09: quantidade > 0; mesma peça soma; peça inativa recusada
    url_pecas = f"/api/mnt/chamados/{os_['id']}/pecas"
    assert cliente.post(url_pecas, headers=tec, json={"peca_id": fabrica["sensor"], "quantidade": 0}).status_code == 422
    cliente.post(url_pecas, headers=tec, json={"peca_id": fabrica["sensor"], "quantidade": 1})
    r = cliente.post(url_pecas, headers=tec, json={"peca_id": fabrica["sensor"], "quantidade": 1.5})
    assert [(p["codigo_peca"], p["quantidade"]) for p in r.json()["pecas"]] == [("PN-SEN-030", 2.5)]
    assert cliente.post(url_pecas, headers=tec, json={"peca_id": fabrica["velha"], "quantidade": 1}).status_code == 422

    # Laudo parcial pode ser salvo (rascunho)
    r = cliente.put(f"/api/mnt/chamados/{os_['id']}/laudo", headers=tec, json={"diagnostico_tecnico": "Sensor sujo"})
    assert r.status_code == 200 and r.json()["diagnostico_tecnico"] == "Sensor sujo"

    # RN04: concluir sem causa raiz é recusado
    url_concluir = f"/api/mnt/chamados/{os_['id']}/concluir"
    sem_causa = {"diagnostico_tecnico": "Troca do sensor", "causa_raiz": "", "tipo_manutencao": "CORRETIVA"}
    assert cliente.post(url_concluir, headers=tec, json=sem_causa).status_code == 422

    # RN03: outro técnico não conclui (nem mexe no laudo / peças)
    laudo = {"diagnostico_tecnico": "Substituídos sensores e recalibrado eixo Z", "causa_raiz": "Falha de sensor / calibração", "tipo_manutencao": "CORRETIVA"}
    assert cliente.post(url_concluir, headers=tec2, json=laudo).status_code == 403
    assert cliente.post(url_pecas, headers=tec2, json={"peca_id": fabrica["sensor"], "quantidade": 1}).status_code == 403

    # Conclusão 75 min depois do início do atendimento: downtime = 90 min desde a abertura (RN05)
    relogio.avancar(75)
    r = cliente.post(url_concluir, headers=tec, json=laudo)
    assert r.status_code == 200, r.text
    fim = r.json()
    assert fim["status_chamado"] == "CONCLUIDO" and fim["downtime_minutos"] == 90
    assert status_maquina(cliente, tec, smt) == "OPERACIONAL"
    assert fim["minutos_desde_abertura"] is None  # só em OS ativa

    # OS encerrada não recebe mais peças nem laudo
    assert cliente.post(url_pecas, headers=tec, json={"peca_id": fabrica["sensor"], "quantidade": 1}).status_code == 409

    # RN08: 3 transições de status para essa OS
    trilha = cliente.get(f"/api/mnt/auditoria?equipamento_id={smt}", headers=token_de("GES-0001")).json()
    transicoes = [(a["status_anterior"], a["status_novo"]) for a in reversed(trilha) if a["chamado_id"] == os_["id"]]
    assert transicoes == [("OPERACIONAL", "PARADA"), ("PARADA", "EM_MANUTENCAO"), ("EM_MANUTENCAO", "OPERACIONAL")]


def test_gestao_conclui_os_de_outro_tecnico(cliente, fabrica, token_de):
    os_id = abrir(cliente, token_de("OPE-0001"), fabrica["smt"]).json()["id"]
    cliente.post(f"/api/mnt/chamados/{os_id}/assumir", headers=token_de("TEC-2001"))
    laudo = {"diagnostico_tecnico": "Ajuste", "causa_raiz": "Erro de operação", "tipo_manutencao": "CORRETIVA"}
    r = cliente.post(f"/api/mnt/chamados/{os_id}/concluir", headers=token_de("GES-0001"), json=laudo)
    assert r.status_code == 200
    assert r.json()["tecnico_nome"] == "João Lima"  # o responsável continua sendo o técnico


# ---------------------------------------------------------------- permissões por persona


@pytest.mark.parametrize("matricula", ["QUA-0001", "ALM-0001"])
def test_personas_sem_acesso_ao_modulo(cliente, fabrica, token_de, matricula):
    assert cliente.get("/api/mnt/equipamentos", headers=token_de(matricula)).status_code == 403


def test_matriz_de_acoes_por_persona(cliente, fabrica, token_de):
    ope, tec, ges = token_de("OPE-0001"), token_de("TEC-2001"), token_de("GES-0001")

    # Todos os perfis operacionais da manutenção podem registrar uma falha.
    os_id = abrir(cliente, ope, fabrica["smt"]).json()["id"]
    assert abrir(cliente, tec, fabrica["test"]).status_code == 201
    assert abrir(cliente, ges, fabrica["qc"]).status_code == 201
    # A restrição de uma OS ativa por máquina continua valendo.
    assert abrir(cliente, tec, fabrica["smt"]).status_code == 409

    # Operador e Supervisor não assumem nem veem... a fila (Supervisor vê)
    assert cliente.post(f"/api/mnt/chamados/{os_id}/assumir", headers=ope).status_code == 403
    assert cliente.post(f"/api/mnt/chamados/{os_id}/assumir", headers=ges).status_code == 403
    assert cliente.get("/api/mnt/chamados/fila", headers=ope).status_code == 403
    assert cliente.get("/api/mnt/chamados/fila", headers=ges).status_code == 200

    # Cadastros, indicadores e auditoria: só gestão
    for rota in ("/api/mnt/indicadores", "/api/mnt/graficos", "/api/mnt/auditoria"):
        assert cliente.get(rota, headers=ope).status_code == 403
        assert cliente.get(rota, headers=tec).status_code == 403
        assert cliente.get(rota, headers=ges).status_code == 200
    nova = {"codigo_tag": "smt-09", "nome": "Nova", "setor": "SMT"}
    assert cliente.post("/api/mnt/equipamentos", headers=tec, json=nova).status_code == 403

    # Todos do módulo consultam máquinas e chamados
    for h in (ope, tec, ges):
        assert cliente.get("/api/mnt/equipamentos", headers=h).status_code == 200
        assert cliente.get(f"/api/mnt/chamados/{os_id}", headers=h).status_code == 200


def test_opcoes_informam_permissoes_da_persona(cliente, fabrica, token_de):
    p_ope = cliente.get("/api/mnt/opcoes", headers=token_de("OPE-0001")).json()["permissoes"]
    p_tec = cliente.get("/api/mnt/opcoes", headers=token_de("TEC-2001")).json()["permissoes"]
    p_adm = cliente.get("/api/mnt/opcoes", headers=token_de("ADM-0001")).json()["permissoes"]
    assert p_ope == {"abrir_chamado": True, "atender": False, "concluir_qualquer": False, "cancelar": False, "cadastros": False, "indicadores": False}
    assert p_tec["atender"] and p_tec["abrir_chamado"]
    assert all(p_adm.values())


# ---------------------------------------------------------------- preventiva e cancelamento


def test_preventiva_nao_para_a_maquina_ate_ser_assumida(cliente, fabrica, token_de, relogio):
    tec, ges = token_de("TEC-2001"), token_de("GES-0001")
    r = cliente.post("/api/mnt/preventivas", headers=tec, json={"equipamento_id": fabrica["test"]})
    assert r.status_code == 201
    prev = r.json()
    assert prev["tipo_manutencao"] == "PREVENTIVA" and prev["status_chamado"] == "ABERTO"
    assert status_maquina(cliente, tec, fabrica["test"]) == "OPERACIONAL"

    # Programada e não iniciada: não conta como downtime
    relogio.avancar(120)
    assert cliente.get("/api/mnt/indicadores", headers=ges).json()["downtime_total_minutos"] == 0

    cliente.post(f"/api/mnt/chamados/{prev['id']}/assumir", headers=tec)
    assert status_maquina(cliente, tec, fabrica["test"]) == "EM_MANUTENCAO"
    # Operador não programa preventiva
    assert cliente.post("/api/mnt/preventivas", headers=token_de("OPE-0001"), json={"equipamento_id": fabrica["smt"]}).status_code == 403


def test_cancelamento_pela_gestao(cliente, fabrica, token_de):
    ope, ges = token_de("OPE-0001"), token_de("GES-0001")
    os_id = abrir(cliente, ope, fabrica["smt"]).json()["id"]
    assert cliente.post(f"/api/mnt/chamados/{os_id}/cancelar", headers=ope, json={"motivo": "Alarme falso"}).status_code == 403
    assert cliente.post(f"/api/mnt/chamados/{os_id}/cancelar", headers=ges, json={"motivo": "x"}).status_code == 422

    r = cliente.post(f"/api/mnt/chamados/{os_id}/cancelar", headers=ges, json={"motivo": "Alarme falso do sensor"})
    assert r.status_code == 200
    c = r.json()
    assert (c["status_chamado"], c["motivo_cancelamento"], c["downtime_minutos"]) == ("CANCELADO", "Alarme falso do sensor", 0)
    assert c["diagnostico_tecnico"] is None  # o motivo não sobrescreve mais o diagnóstico
    assert status_maquina(cliente, ope, fabrica["smt"]) == "OPERACIONAL"
    # Já encerrada: não cancela de novo; e a máquina aceita chamado novo
    assert cliente.post(f"/api/mnt/chamados/{os_id}/cancelar", headers=ges, json={"motivo": "De novo"}).status_code == 409
    assert abrir(cliente, ope, fabrica["smt"]).status_code == 201


# ---------------------------------------------------------------- cadastros (RN07)


def test_cadastro_de_maquinas_e_soft_delete(cliente, fabrica, token_de):
    ges, ope = token_de("GES-0001"), token_de("OPE-0001")
    r = cliente.post("/api/mnt/equipamentos", headers=ges, json={"codigo_tag": " smt-04 ", "nome": "Nova insersora", "setor": "SMT"})
    assert r.status_code == 201 and r.json()["codigo_tag"] == "SMT-04"
    assert cliente.post("/api/mnt/equipamentos", headers=ges, json={"codigo_tag": "SMT-04", "nome": "X", "setor": "SMT"}).status_code == 409

    # Não inativa máquina com OS ativa
    abrir(cliente, ope, fabrica["smt"])
    assert cliente.patch(f"/api/mnt/equipamentos/{fabrica['smt']}", headers=ges, json={"ativo": False}).status_code == 409

    # Inativa: some do painel, aparece com incluir_inativos, e não recebe chamado
    nova = r.json()["id"]
    assert cliente.patch(f"/api/mnt/equipamentos/{nova}", headers=ges, json={"ativo": False}).json()["ativo"] is False
    assert nova not in [e["id"] for e in cliente.get("/api/mnt/equipamentos", headers=ope).json()]
    assert nova in [e["id"] for e in cliente.get("/api/mnt/equipamentos?incluir_inativos=true", headers=ges).json()]
    assert abrir(cliente, ope, nova).status_code == 409


def test_cadastro_de_pecas(cliente, fabrica, token_de):
    ges = token_de("GES-0001")
    r = cliente.post("/api/mnt/pecas", headers=ges, json={"codigo_peca": "pn-rol-608", "nome": "Rolamento", "unidade_medida": "un"})
    assert r.status_code == 201 and (r.json()["codigo_peca"], r.json()["unidade_medida"]) == ("PN-ROL-608", "UN")
    assert cliente.post("/api/mnt/pecas", headers=ges, json={"codigo_peca": "PN-ROL-608", "nome": "X"}).status_code == 409
    ativas = [p["codigo_peca"] for p in cliente.get("/api/mnt/pecas", headers=ges).json()]
    assert "PN-OLD-001" not in ativas and "PN-ROL-608" in ativas


def test_painel_mostra_os_ativa_e_paradas_primeiro(cliente, fabrica, token_de):
    ope = token_de("OPE-0001")
    abrir(cliente, ope, fabrica["test"], descricao="Erro de comunicação no barramento")
    painel = cliente.get("/api/mnt/equipamentos", headers=ope).json()
    assert painel[0]["codigo_tag"] == "TEST-01" and painel[0]["status_operacional"] == "PARADA"
    assert painel[0]["os_ativa"]["descricao_falha"] == "Erro de comunicação no barramento"
    assert all(e["os_ativa"] is None for e in painel[1:])


# ---------------------------------------------------------------- consultas


def test_filtros_do_historico(cliente, fabrica, token_de, relogio):
    ope, ope2, ges = token_de("OPE-0001"), token_de("OPE-0002"), token_de("GES-0001")
    a = abrir(cliente, ope, fabrica["smt"], descricao="Correia do alimentador travando").json()
    relogio.avancar(60 * 24 * 2)  # dois dias depois
    b = abrir(cliente, ope2, fabrica["test"], descricao="Sonda pneumática sem resposta").json()
    cliente.post(f"/api/mnt/chamados/{a['id']}/cancelar", headers=ges, json={"motivo": "Duplicado"})

    def ids(query: str, h=ges):
        return [c["id"] for c in cliente.get(f"/api/mnt/chamados{query}", headers=h).json()]

    assert ids("") == [b["id"], a["id"]]  # mais recentes primeiro
    assert ids("?meus_abertos=true", h=ope) == [a["id"]]
    assert ids("?status=ABERTO&status=EM_ANDAMENTO") == [b["id"]]
    assert ids("?busca=correia") == [a["id"]]
    assert ids("?setor=Testes%20Funcionais") == [b["id"]]
    assert ids("?de=2026-11-12") == [b["id"]]
    assert ids("?ate=2026-11-10") == [a["id"]]


def test_indicadores_com_relogio_controlado(cliente, fabrica, token_de, relogio):
    """2 OS concluídas: (resposta 10, reparo 50, downtime 60) e (resposta 20, reparo 100, downtime 120)."""
    ope, tec, ges = token_de("OPE-0001"), token_de("TEC-2001"), token_de("GES-0001")
    laudo = {"diagnostico_tecnico": "Ajuste", "causa_raiz": "Desalinhamento mecânico", "tipo_manutencao": "CORRETIVA"}
    for maquina, resposta, reparo in ((fabrica["smt"], 10, 50), (fabrica["test"], 20, 100)):
        os_id = abrir(cliente, ope, maquina).json()["id"]
        relogio.avancar(resposta)
        cliente.post(f"/api/mnt/chamados/{os_id}/assumir", headers=tec)
        relogio.avancar(reparo)
        cliente.post(f"/api/mnt/chamados/{os_id}/concluir", headers=tec, json=laudo)

    ind = cliente.get("/api/mnt/indicadores", headers=ges).json()
    assert ind["downtime_total_minutos"] == 180
    assert ind["mtta_minutos"] == 15.0
    assert ind["mttr_minutos"] == 75.0
    # 3 máquinas × 600 min = 1800 programados; 1800 - 180 = 1620 operando; 2 falhas corretivas
    assert ind["disponibilidade_pct"] == 90.0
    assert ind["mtbf_minutos"] == 810.0
    assert (ind["chamados_concluidos"], ind["total_maquinas"], ind["maquinas_operacionais"]) == (2, 3, 3)

    g = cliente.get("/api/mnt/graficos", headers=ges).json()
    assert g["downtime_por_maquina"][0]["codigo_tag"] == "TEST-01"
    assert g["chamados_por_causa_raiz"] == [{"causa_raiz": "Desalinhamento mecânico", "chamados": 2, "downtime_minutos": 180}]
    assert g["evolucao_diaria"] == [{"data": "2026-11-10", "chamados": 2, "downtime_minutos": 180}]


# ---------------------------------------------------------------- integração e banco


def test_abertura_por_outro_modulo_nao_duplica(sessao, fabrica):
    """Substitui o POST /api/manutencao/chamados com chave: agora a Qualidade chama a função direto."""
    inspetora = fabrica["u"]["qua"]
    sessao.add(inspetora)
    c1, criado1 = servico.abrir_chamado_por_tag(
        sessao, equipamento_tag="qc-01", executor=inspetora, descricao_falha="Câmera de inspeção desalinhada",
        prioridade=Prioridade.ALTA, origem_sistema="Qualidade", id_externo="QLD-42",
    )
    c2, criado2 = servico.abrir_chamado_por_tag(
        sessao, equipamento_tag="QC-01", executor=inspetora, descricao_falha="Câmera de inspeção desalinhada",
        origem_sistema="qualidade", id_externo="QLD-42",
    )
    assert (criado1, criado2) == (True, False) and c1.id == c2.id
    assert (c1.origem_sistema, c1.operador.nome) == ("qualidade", "Maria")
    assert sessao.get(Equipamento, fabrica["qc"]).status_operacional == "PARADA"


def test_banco_garante_uma_os_ativa_por_maquina(sessao, fabrica):
    """RN02 no próprio banco: mesmo pulando o serviço, não entra uma segunda OS ativa."""
    ope = fabrica["u"]["ope"]
    base = dict(equipamento_id=fabrica["smt"], operador_abertura_id=ope.id, prioridade="ALTA", descricao_falha="Falha", data_hora_abertura=INICIO)
    sessao.add(Chamado(**base, status_chamado="ABERTO"))
    sessao.commit()
    sessao.add(Chamado(**base, status_chamado="CONCLUIDO"))  # encerrada: pode
    sessao.commit()
    sessao.add(Chamado(**base, status_chamado="EM_ANDAMENTO"))
    with pytest.raises(IntegrityError):
        sessao.commit()
    sessao.rollback()
