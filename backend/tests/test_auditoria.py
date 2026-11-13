"""Trilha de auditoria (usr.auditoria e /api/auditoria): gravada sozinha nos flushes, com quem fez e os campos
antes e depois; sem senhas; consultada só por Administrador e Supervisor."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.core import tempo
from app.core.rbac import Perfil
from app.modulos.auditoria import registro
from app.modulos.auditoria.modelos import RegistroAuditoria
from app.modulos.manutencao.modelos import Equipamento
from app.modulos.qualidade.modelos import Estacao, Produto, TipoDefeito

AGORA = datetime(2026, 11, 13, 15, 0, tzinfo=UTC)


@pytest.fixture
def base(sessao, criar_usuario, monkeypatch):
    monkeypatch.setattr(tempo, "agora", lambda: AGORA)
    u = {
        "adm": criar_usuario("ADM-0001", Perfil.ADMINISTRADOR, nome="Ana"),
        "ges": criar_usuario("GES-0001", Perfil.SUPERVISOR, nome="Orlando"),
        "qua": criar_usuario("QUA-0001", Perfil.INSPETOR, nome="Maria"),
        "ope": criar_usuario("OPE-0001", Perfil.OPERADOR, nome="João"),
    }
    itens = [Equipamento(codigo_tag="TEST-02", nome="Testador", setor="Testes"), Produto(numero_serie="AMT-000017", modelo="AMT N16"),
             Estacao(nome="Teste Funcional"), TipoDefeito(nome="Tela")]
    registro.desligar(sessao)  # a preparação não entra na trilha
    sessao.add_all(itens)
    sessao.commit()
    sessao.info.pop(registro.CHAVE_DESLIGADA)
    return {"u": u, "ids": [i.id for i in itens]}


def ocorrencia(base, **extra):
    maquina, produto, estacao, tipo = base["ids"]
    return {"ocorrida_em": "2026-11-13T08:30:00", "classificacao": "MAIOR", "situacao_produto": "REPROVADO",
            "status": "ABERTA", "observacao": "Tela com linhas.", "acao_realizada": "Retido.", "produto_id": produto,
            "estacao_id": estacao, "tipo_defeito_id": tipo, "equipamento_id": maquina, **extra}


def trilha(cliente, h, **params):
    r = cliente.get("/api/auditoria", headers=h, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_criar_e_editar_ficam_na_trilha_com_quem_fez(cliente, token_de, base):
    r = cliente.post("/api/qld/ocorrencias", headers=token_de("QUA-0001"), json=ocorrencia(base))
    oc = r.json()["ocorrencia"]["id"]
    cliente.put(f"/api/qld/ocorrencias/{oc}", headers=token_de("OPE-0001"), json=ocorrencia(base, status="RESOLVIDA"))

    linhas = trilha(cliente, token_de("GES-0001"), entidade="qld.ocorrencias", entidade_id=str(oc))
    assert [(l["acao"], l["usuario_nome"]) for l in linhas] == [("ALTEROU", "João"), ("CRIOU", "Maria")]
    alterou, criou = linhas
    assert alterou["descricao"] == f"Ocorrência #{oc}" and alterou["modulo"] == "QLD"
    assert alterou["alteracoes"] == {"status": ["ABERTA", "RESOLVIDA"]}  # só o que mudou
    assert criou["alteracoes"]["status"] == [None, "ABERTA"] and criou["alteracoes"]["observacao"] == [None, "Tela com linhas."]


def test_senha_nunca_entra_na_trilha(cliente, token_de, base, sessao):
    h = token_de("ADM-0001")
    ope = base["u"]["ope"].id
    assert cliente.post(f"/api/usuarios/{ope}/senha", headers=h, json={"nova_senha": "outra-senha-123"}).status_code == 204
    assert cliente.patch(f"/api/usuarios/{ope}", headers=h, json={"perfil": Perfil.INSPETOR.value}).status_code == 200

    linhas = trilha(cliente, h, modulo="USR", acao="ALTEROU")
    assert [l["descricao"] for l in linhas] == ["Usuário OPE-0001"]  # a troca de senha sozinha não gera linha
    assert linhas[0]["alteracoes"] == {"perfil": [Perfil.OPERADOR.value, Perfil.INSPETOR.value]}
    assert linhas[0]["usuario_matricula"] == "ADM-0001"
    textos = [str(r.alteracoes) for r in sessao.scalars(select(RegistroAuditoria))]
    assert not any("senha" in t for t in textos)


def test_so_administrador_e_supervisor_consultam(cliente, token_de, base):
    assert cliente.get("/api/auditoria", headers=token_de("ADM-0001")).status_code == 200
    assert cliente.get("/api/auditoria", headers=token_de("GES-0001")).status_code == 200
    assert cliente.get("/api/auditoria", headers=token_de("QUA-0001")).status_code == 403
    assert cliente.get("/api/auditoria", headers=token_de("OPE-0001")).status_code == 403


def test_filtros(cliente, token_de, base):
    cliente.post("/api/qld/ocorrencias", headers=token_de("QUA-0001"), json=ocorrencia(base))
    cliente.post("/api/qld/estacoes", headers=token_de("GES-0001"), json={"nome": "Embalagem"})
    h = token_de("ADM-0001")
    da_maria = trilha(cliente, h, busca="maria")  # pela pessoa
    assert [l["descricao"] for l in da_maria] == ["Ocorrência #1"] and da_maria[0]["usuario_nome"] == "Maria"
    assert [l["descricao"] for l in trilha(cliente, h, busca="Embalagem")] == ["Estação Embalagem"]
    assert all(l["acao"] == "CRIOU" for l in trilha(cliente, h, acao="CRIOU"))
    assert trilha(cliente, h, de="2026-11-14") == []


def test_desligada_nao_grava(sessao, base):
    registro.desligar(sessao)
    sessao.add(Estacao(nome="Inserção Manual"))
    sessao.commit()
    estacoes = select(func.count()).select_from(RegistroAuditoria).where(RegistroAuditoria.entidade == "qld.estacoes")
    assert sessao.scalar(estacoes) == 0


def test_criado_e_alterado_na_mesma_operacao_vira_uma_linha_com_o_valor_final(sessao, base):
    from app.modulos.qualidade.modelos import Estacao as E

    estacao = E(nome="TMP-provisorio")
    sessao.add(estacao)
    sessao.flush()
    estacao.nome = "Embalagem final"  # como a produção que ganha o número de série depois de ter id
    sessao.commit()
    linhas = list(sessao.scalars(select(RegistroAuditoria).where(RegistroAuditoria.entidade == "qld.estacoes")))
    assert [(l.acao, l.descricao) for l in linhas] == [("CRIOU", "Estação Embalagem final")]
    assert linhas[0].alteracoes["nome"] == [None, "Embalagem final"]

    estacao.descricao = "Linha 2"  # outra operação: aí sim é uma alteração
    sessao.commit()
    assert sessao.scalar(select(func.count()).select_from(RegistroAuditoria).where(
        RegistroAuditoria.entidade == "qld.estacoes", RegistroAuditoria.acao == "ALTEROU")) == 1
