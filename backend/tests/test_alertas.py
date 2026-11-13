"""Alertas do sino (/api/alertas): situação aberta vira alerta para os perfis certos, some quando resolve, não
duplica e o "lido" é de cada pessoa."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core import tempo
from app.core.rbac import Perfil
from app.modulos.alertas.modelos import Alerta
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.rastreabilidade.constantes import ETAPAS_PADRAO
from app.modulos.rastreabilidade.modelos import Componente, Etapa, Modelo, Producao, Solicitacao

AGORA = datetime(2026, 11, 13, 15, 0, tzinfo=UTC)


@pytest.fixture
def relogio(monkeypatch):
    estado = {"agora": AGORA}
    monkeypatch.setattr(tempo, "agora", lambda: estado["agora"])
    return estado


@pytest.fixture
def base(sessao, criar_usuario, relogio):
    u = {m: criar_usuario(m, p, nome=m) for m, p in (
        ("ADM-0001", Perfil.ADMINISTRADOR), ("GES-0001", Perfil.SUPERVISOR), ("TEC-2001", Perfil.TECNICO),
        ("ALM-0001", Perfil.ALMOXARIFE), ("QUA-0001", Perfil.INSPETOR), ("OPE-0001", Perfil.OPERADOR))}
    maquina = Equipamento(codigo_tag="TEST-02", nome="Testador", setor="Testes", status_operacional="PARADA")
    sessao.add(maquina)
    sessao.commit()
    return {"u": u, "maquina": maquina}


def chamado(sessao, base, *, prioridade: str, minutos_atras: int) -> Chamado:
    c = Chamado(equipamento_id=base["maquina"].id, operador_abertura_id=base["u"]["OPE-0001"].id, prioridade=prioridade,
                status_chamado="ABERTO", descricao_falha="Sondas sem contato",
                data_hora_abertura=AGORA - timedelta(minutes=minutos_atras))
    sessao.add(c)
    sessao.commit()
    return c


def alertas(cliente, token_de, matricula: str) -> dict:
    r = cliente.get("/api/alertas", headers=token_de(matricula))
    assert r.status_code == 200, r.text
    return r.json()


def test_os_de_prioridade_alta_avisa_tecnico_e_resolve_ao_assumir(cliente, token_de, base, sessao):
    c = chamado(sessao, base, prioridade="ALTA", minutos_atras=5)
    tec = alertas(cliente, token_de, "TEC-2001")
    assert tec["nao_lidos"] == 1
    assert [(a["titulo"], a["link"], a["ativo"]) for a in tec["alertas"]] == [
        (f"OS #{c.id} aberta: TEST-02", f"/manutencao/ordens/{c.id}", True)]
    assert alertas(cliente, token_de, "ALM-0001")["alertas"] == []  # almoxarife não recebe OS

    c.status_chamado = "EM_ANDAMENTO"
    sessao.commit()
    tec = alertas(cliente, token_de, "TEC-2001")
    assert tec["nao_lidos"] == 0
    assert [a["ativo"] for a in tec["alertas"]] == [False]  # resolvido, ainda visível por 24 h


def test_maquina_parada_sem_tecnico_depois_de_30_minutos(cliente, token_de, base, sessao, relogio):
    chamado(sessao, base, prioridade="MEDIA", minutos_atras=20)  # média: sem alerta de OS
    assert alertas(cliente, token_de, "GES-0001")["alertas"] == []
    relogio["agora"] = AGORA + timedelta(minutes=15)
    ges = alertas(cliente, token_de, "GES-0001")
    assert [a["tipo"] for a in ges["alertas"]] == ["PARADA_SEM_TECNICO"]
    assert ges["alertas"][0]["titulo"] == "TEST-02 parada há mais de 30 min sem técnico"
    assert alertas(cliente, token_de, "TEC-2001")["alertas"] == []  # vai para quem coordena


def test_estoque_insuficiente_atualiza_o_detalhe_e_resolve(cliente, token_de, base, sessao):
    etapas = [Etapa(nome=n, ordem=o) for n, o in ETAPAS_PADRAO]
    modelo, bateria = Modelo(codigo="N14", nome="AMT N14"), Componente(sku="BAT-45WH", nome="Bateria", estoque=4)
    sessao.add_all([*etapas, modelo, bateria])
    sessao.commit()
    ope = base["u"]["OPE-0001"].id
    p = Producao(numero_serie="AMT-000031", id_unica="PRD-31", modelo_id=modelo.id, etapa_id=etapas[0].id,
                 responsavel_id=ope, criado_por_id=ope, iniciada_em=AGORA, atualizada_em=AGORA)
    sessao.add(p)
    sessao.commit()
    sessao.add(Solicitacao(producao_id=p.id, componente_id=bateria.id, quantidade=18, status="PENDENTE",
                           criado_por_id=ope, criada_em=AGORA))
    sessao.commit()

    alm = alertas(cliente, token_de, "ALM-0001")["alertas"]
    assert [(a["titulo"], a["detalhe"]) for a in alm] == [("BAT-45WH sem estoque suficiente", "4 em estoque para 18 pedido(s) em aberto · Bateria")]
    primeiro = alm[0]["id"]

    bateria.estoque = 10
    sessao.commit()
    alm = alertas(cliente, token_de, "ALM-0001")["alertas"]
    assert (alm[0]["id"], alm[0]["detalhe"][:2]) == (primeiro, "10")  # o mesmo alerta, com o número novo

    bateria.estoque = 30
    sessao.commit()
    assert [a["ativo"] for a in alertas(cliente, token_de, "ALM-0001")["alertas"]] == [False]


def test_ocorrencia_critica_avisa_inspetor(cliente, token_de, base, sessao):
    produto, estacao, tipo = Produto(numero_serie="AMT-000017", modelo="AMT N16"), Estacao(nome="Teste Funcional"), TipoDefeito(nome="Tela")
    sessao.add_all([produto, estacao, tipo])
    sessao.commit()
    oc = Ocorrencia(ocorrida_em=AGORA - timedelta(hours=1), classificacao="CRITICO", situacao_produto="REPROVADO",
                    status="ABERTA", observacao="x", acao_realizada="y", produto_id=produto.id, estacao_id=estacao.id,
                    tipo_defeito_id=tipo.id, equipamento_id=base["maquina"].id, responsavel_id=base["u"]["QUA-0001"].id)
    sessao.add(oc)
    sessao.commit()
    qua = alertas(cliente, token_de, "QUA-0001")["alertas"]
    assert [a["titulo"] for a in qua] == [f"Ocorrência crítica #{oc.id}: Tela"]
    oc.status = "RESOLVIDA"
    sessao.commit()
    assert [a["ativo"] for a in alertas(cliente, token_de, "QUA-0001")["alertas"]] == [False]


def test_nao_duplica_e_lido_e_de_cada_pessoa(cliente, token_de, base, sessao):
    chamado(sessao, base, prioridade="CRITICA", minutos_atras=1)
    for _ in range(3):
        alertas(cliente, token_de, "TEC-2001")
        alertas(cliente, token_de, "GES-0001")
    assert sessao.scalar(select(func.count()).select_from(Alerta)) == 1

    assert cliente.post("/api/alertas/lidos", headers=token_de("TEC-2001"), json={}).status_code == 204
    assert alertas(cliente, token_de, "TEC-2001")["nao_lidos"] == 0
    assert alertas(cliente, token_de, "TEC-2001")["alertas"][0]["lido"] is True
    assert alertas(cliente, token_de, "GES-0001")["nao_lidos"] == 1
