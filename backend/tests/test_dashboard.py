"""Testes do Dashboard (/api/dsh).

O caso de referência do enunciado (15/08/2026, 1º turno, meta 1.500, 1.420 produzidos, 60 reprovados, 85 min de
parada -> 94,7%, 4,2% e 215,7 un/h) é o mesmo dos testes do sistema antigo, agora com os dados vindos da RAS e da MNT.
"""
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import insert, select

from app.core import tempo
from app.core.rbac import Perfil
from app.modulos.dashboard.constantes import LIMITES_PADRAO, TIPOS_PERDA_PADRAO, TURNOS_PADRAO
from app.modulos.dashboard.modelos import Limite, Meta, TipoPerda, Turno
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.rastreabilidade.constantes import ETAPAS_PADRAO
from app.modulos.rastreabilidade.modelos import Etapa, Modelo, Passagem, Producao

DIA = date(2026, 8, 15)
AGORA = datetime(2026, 8, 16, 15, 0, tzinfo=UTC)  # 11:00 de 16/08 em Manaus


def manaus(dia: date, hora: int, minuto: int = 0) -> datetime:
    """Horário de Manaus (UTC-4) em UTC."""
    return datetime(dia.year, dia.month, dia.day, hora, minuto, tzinfo=tempo.FUSO_FABRICA).astimezone(UTC)


@pytest.fixture
def dsh(sessao, criar_usuario, monkeypatch):
    monkeypatch.setattr(tempo, "agora", lambda: AGORA)
    u = {
        "adm": criar_usuario("ADM-0001", Perfil.ADMINISTRADOR, nome="Ana"),
        "ges": criar_usuario("GES-0001", Perfil.SUPERVISOR, nome="Orlando"),
        "ope": criar_usuario("OPE-0001", Perfil.OPERADOR, nome="João"),
        "tec": criar_usuario("TEC-2001", Perfil.TECNICO, nome="João Lima"),
        "alm": criar_usuario("ALM-0001", Perfil.ALMOXARIFE, nome="Carlos"),
    }
    turnos = [Turno(nome=n, hora_inicio=i, hora_fim=f) for n, i, f in TURNOS_PADRAO]
    sessao.add_all(turnos)
    sessao.add_all(Limite(indicador=i.value, limite_verde=v, limite_amarelo=a, sentido=s.value) for i, v, a, s in LIMITES_PADRAO)
    sessao.add_all(TipoPerda(nome=n) for n in TIPOS_PERDA_PADRAO)
    etapas = {n: Etapa(nome=n, ordem=o) for n, o in ETAPAS_PADRAO}
    modelos = [Modelo(codigo="N14-I5-8-256", nome="AMT N14"), Modelo(codigo="N16-I7-16-512", nome="AMT N16")]
    estacoes = [Estacao(nome="Teste Funcional"), Estacao(nome="Montagem Final")]
    maquina = Equipamento(codigo_tag="TEST-02", nome="Testador 02", setor="Testes Funcionais")
    sessao.add_all([*etapas.values(), *modelos, *estacoes, maquina, TipoDefeito(nome="Tela")])
    sessao.commit()
    producoes = []
    for i, m in enumerate(modelos, start=1):
        p = Producao(numero_serie=f"AMT-{i:06d}", id_unica=f"PRD-{i}", modelo_id=m.id, etapa_id=etapas["Em Fila"].id,
                     responsavel_id=u["ope"].id, criado_por_id=u["ope"].id, iniciada_em=manaus(DIA, 6),
                     atualizada_em=manaus(DIA, 6))
        producoes.append(p)
    sessao.add_all(producoes)
    sessao.commit()
    return {"u": u, "turno": [t.id for t in turnos], "etapa": {n: e.id for n, e in etapas.items()},
            "modelo": [m.id for m in modelos], "producao": [p.id for p in producoes], "estacao": [e.id for e in estacoes],
            "maquina": maquina.id}


def passagens(sessao, dsh, quando: datetime, *, aprovadas=0, reprovadas=0, modelo=0):
    linhas = [{"producao_id": dsh["producao"][modelo], "etapa_id": dsh["etapa"][etapa], "usuario_id": dsh["u"]["ope"].id,
               "registrada_em": quando, "origem": "MANUAL"}
              for etapa, n in (("Aprovado", aprovadas), ("Reprovado", reprovadas)) for _ in range(n)]
    if linhas:
        sessao.execute(insert(Passagem), linhas)
    sessao.commit()


def meta(sessao, dsh, quantidade, dia=DIA, turno=0, modelo=0):
    sessao.add(Meta(data=dia, turno_id=dsh["turno"][turno], modelo_id=dsh["modelo"][modelo], quantidade=quantidade,
                    registrado_por_id=dsh["u"]["ges"].id, registrado_em=AGORA))
    sessao.commit()


def chamado(sessao, dsh, abertura: datetime, *, fim: datetime | None = None, downtime: int | None = None,
            status="CONCLUIDO") -> Chamado:
    c = Chamado(equipamento_id=dsh["maquina"], operador_abertura_id=dsh["u"]["ope"].id, prioridade="ALTA",
                status_chamado=status, descricao_falha="Sondas do ICT sem contato", data_hora_abertura=abertura,
                data_hora_fim_atendimento=fim, downtime_minutos=downtime)
    sessao.add(c)
    sessao.commit()
    return c


def painel(cliente, h, **params):
    r = cliente.get("/api/dsh/painel", headers=h, params={"de": DIA.isoformat(), "ate": DIA.isoformat(), **params})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- indicadores


def test_caso_de_referencia_do_enunciado(cliente, token_de, dsh, sessao):
    passagens(sessao, dsh, manaus(DIA, 10), aprovadas=1360, reprovadas=60)
    meta(sessao, dsh, 1500)
    chamado(sessao, dsh, manaus(DIA, 8), fim=manaus(DIA, 9, 25), downtime=85)

    p = painel(cliente, token_de("GES-0001"))
    assert p["producao"] == {"realizada": 1420, "aprovada": 1360, "reprovada": 60, "meta": 1500}
    assert p["atendimento_meta"] == {"valor": 94.7, "semaforo": "amarelo"}
    assert p["indice_defeitos"] == {"valor": 4.2, "semaforo": "amarelo"}
    assert p["produtividade"] == {"valor": 215.7, "minutos_turno": 480, "minutos_produtivos": 395}
    assert p["tempo_parada"] == {"minutos": 85, "paradas": 1, "em_andamento": 0}
    assert p["graficos"]["producao_x_meta"] == [{"modelo": "AMT N14", "realizada": 1420, "meta": 1500}]
    assert p["graficos"]["parada_por_turno"] == [{"rotulo": "1º turno", "minutos": 85}, {"rotulo": "2º turno", "minutos": 0}]


def test_dia_e_turno_da_fabrica(cliente, token_de, dsh, sessao):
    passagens(sessao, dsh, manaus(DIA, 21, 30), aprovadas=2)        # 01:30 UTC de 16/08: 2º turno de 15/08
    passagens(sessao, dsh, manaus(DIA, 22, 30), aprovadas=5)        # depois do 2º turno: fora
    passagens(sessao, dsh, manaus(DIA, 5, 59), aprovadas=7)         # antes do 1º turno: fora
    passagens(sessao, dsh, manaus(DIA, 6), aprovadas=1, modelo=1)   # 1º turno, outro modelo
    h = token_de("OPE-0001")

    assert painel(cliente, h)["producao"]["realizada"] == 3
    assert painel(cliente, h, turno_id=dsh["turno"][1])["producao"]["realizada"] == 2
    assert painel(cliente, h, modelo_id=dsh["modelo"][1])["producao"]["realizada"] == 1
    assert painel(cliente, h)["produtividade"]["minutos_turno"] == 960  # dois turnos com produção


def test_sem_meta_nao_tem_semaforo(cliente, token_de, dsh, sessao):
    passagens(sessao, dsh, manaus(DIA, 10), aprovadas=10)
    p = painel(cliente, token_de("GES-0001"))
    assert p["atendimento_meta"] == {"valor": None, "semaforo": None}  # RN03: "sem meta", sem dividir por zero
    assert p["indice_defeitos"] == {"valor": 0.0, "semaforo": "verde"}


def test_retrabalho_e_defeitos_vem_da_qualidade(cliente, token_de, dsh, sessao):
    passagens(sessao, dsh, manaus(DIA, 10), aprovadas=18, reprovadas=2)
    produto = Produto(numero_serie="AMT-000001", modelo="AMT N14")
    sessao.add(produto)
    sessao.commit()
    tipo = sessao.scalar(select(TipoDefeito))
    for situacao, estacao, oculta in (("EM_REPROCESSO", 0, False), ("REPROVADO", 0, False), ("EM_REPROCESSO", 1, False),
                                      ("EM_REPROCESSO", 1, True)):
        sessao.add(Ocorrencia(ocorrida_em=manaus(DIA, 11), classificacao="MAIOR", situacao_produto=situacao, status="ABERTA",
                              observacao="x", acao_realizada="y", oculta=oculta, produto_id=produto.id,
                              estacao_id=dsh["estacao"][estacao], tipo_defeito_id=tipo.id, equipamento_id=dsh["maquina"],
                              responsavel_id=dsh["u"]["ges"].id))
    sessao.commit()

    p = painel(cliente, token_de("GES-0001"))
    assert p["indice_retrabalho"] == {"valor": 10.0, "retrabalho": 2, "semaforo": "vermelho"}  # 2 de 20; oculta não conta
    assert p["graficos"]["defeitos_por_estacao"] == [{"rotulo": "Teste Funcional", "quantidade": 2},
                                                     {"rotulo": "Montagem Final", "quantidade": 1}]
    assert painel(cliente, token_de("GES-0001"), modelo_id=dsh["modelo"][1])["indice_retrabalho"]["retrabalho"] == 0


def test_paradas_cancelada_e_em_andamento(cliente, token_de, dsh, sessao):
    chamado(sessao, dsh, manaus(DIA, 7), fim=manaus(DIA, 7, 30), status="CANCELADO", downtime=0)
    ativo = chamado(sessao, dsh, manaus(DIA, 13), status="EM_ANDAMENTO")
    sessao.get(Equipamento, dsh["maquina"]).status_operacional = "EM_MANUTENCAO"
    sessao.commit()

    p = painel(cliente, token_de("TEC-2001"))  # o técnico vê o painel
    # Ativa conta até agora: 13:00 de 15/08 até 11:00 de 16/08 = 22 h.
    assert p["tempo_parada"] == {"minutos": 22 * 60, "paradas": 1, "em_andamento": 1}
    assert [x["chamado_id"] for x in p["paradas_em_andamento"]] == [ativo.id]
    # O aviso de máquina parada não depende do período escolhido.
    outro_dia = cliente.get("/api/dsh/painel", headers=token_de("TEC-2001"), params={"de": "2026-08-01", "ate": "2026-08-01"}).json()
    assert len(outro_dia["paradas_em_andamento"]) == 1 and outro_dia["tempo_parada"]["paradas"] == 0


def test_periodo_invalido(cliente, token_de, dsh):
    h = token_de("GES-0001")
    assert cliente.get("/api/dsh/painel", headers=h, params={"de": "2026-08-16", "ate": "2026-08-15"}).status_code == 422
    assert cliente.get("/api/dsh/painel", headers=h, params={"de": "2025-01-01", "ate": "2026-08-15"}).status_code == 422
    sem_datas = cliente.get("/api/dsh/painel", headers=h).json()
    assert sem_datas["periodo"] == {"de": "2026-08-16", "ate": "2026-08-16"}  # hoje na fábrica


def test_almoxarife_sem_acesso(cliente, token_de, dsh):
    assert cliente.get("/api/dsh/painel", headers=token_de("ALM-0001")).status_code == 403


# ---------------------------------------------------------------- metas, perdas e planilhas


def test_meta_gravada_de_novo_atualiza(cliente, token_de, dsh, sessao):
    h = token_de("GES-0001")
    corpo = {"data": "2026-08-15", "turno_id": dsh["turno"][0], "modelo_id": dsh["modelo"][0], "quantidade": 100}
    assert cliente.put("/api/dsh/metas", headers=token_de("OPE-0001"), json=corpo).status_code == 403
    primeira = cliente.put("/api/dsh/metas", headers=h, json=corpo).json()
    segunda = cliente.put("/api/dsh/metas", headers=h, json={**corpo, "quantidade": 120}).json()
    assert primeira["id"] == segunda["id"] and segunda["quantidade"] == 120  # RN09
    assert len(cliente.get("/api/dsh/metas", headers=h, params={"de": "2026-08-15"}).json()) == 1
    assert cliente.delete(f"/api/dsh/metas/{segunda['id']}", headers=h).status_code == 204


def test_perdas(cliente, token_de, dsh, sessao):
    h = token_de("GES-0001")
    tipo = sessao.scalar(select(TipoPerda).where(TipoPerda.nome == "Componente danificado"))
    corpo = {"data": "2026-08-15", "turno_id": dsh["turno"][0], "estacao_id": dsh["estacao"][1],
             "modelo_id": dsh["modelo"][0], "tipo_perda_id": tipo.id, "quantidade": 3}
    assert cliente.post("/api/dsh/perdas", headers=h, json={**corpo, "quantidade": 0}).status_code == 422  # RN07
    assert cliente.post("/api/dsh/perdas", headers=h, json={**corpo, "data": "2026-08-17"}).status_code == 422  # futuro
    assert cliente.post("/api/dsh/perdas", headers=h, json=corpo).status_code == 201
    p = painel(cliente, h)
    assert p["perdas"] == {"total": 3, "por_tipo": [{"rotulo": "Componente danificado", "quantidade": 3}]}
    assert painel(cliente, h, turno_id=dsh["turno"][1])["perdas"]["total"] == 0


def test_importacao_csv_tudo_ou_nada(cliente, token_de, dsh):
    h = token_de("GES-0001")
    ruim = ("data;turno;estação;modelo;tipo;quantidade;observacao\n"
            "15/08/2026;1º turno;Montagem final;AMT N14;Componente danificado;2;ok\n"
            "2026-08-15;3º turno;Montagem Final;N16-I7-16-512;Material descartado;0;\n")
    r = cliente.post("/api/dsh/importacao/perdas", headers=h, json={"conteudo": ruim}).json()
    assert r["importadas"] == 0 and r["linhas_lidas"] == 2
    assert [(e["linha"], e["coluna"]) for e in r["erros"]] == [(3, "turno"), (3, "quantidade")]
    assert cliente.get("/api/dsh/perdas", headers=h, params={"de": "2026-08-15"}).json() == []

    bom = ruim.replace("3º turno", "2º turno").replace(";0;", ";4;")
    r = cliente.post("/api/dsh/importacao/perdas", headers=h, json={"conteudo": "﻿" + bom}).json()
    assert r == {"linhas_lidas": 2, "importadas": 2, "erros": []}
    perdas = cliente.get("/api/dsh/perdas", headers=h, params={"de": "2026-08-15"}).json()
    assert sorted(p["quantidade"] for p in perdas) == [2, 4] and {p["origem"] for p in perdas} == {"csv"}

    metas = "data,turno,modelo,quantidade\n2026-08-15,1º turno,AMT N14,50\n2026-08-15,1 turno,AMT N14,60\n"
    r = cliente.post("/api/dsh/importacao/metas", headers=h, json={"conteudo": metas}).json()
    assert r["erros"][0]["coluna"] == "turno"
    repetida = "data,turno,modelo,quantidade\n2026-08-15,1º turno,AMT N14,50\n2026-08-15,1º turno,amt n14,60\n"
    r = cliente.post("/api/dsh/importacao/metas", headers=h, json={"conteudo": repetida}).json()
    assert "RN09" in r["erros"][0]["mensagem"]

    sem_coluna = cliente.post("/api/dsh/importacao/metas", headers=h, json={"conteudo": "data;modelo\n2026-08-15;X\n"})
    assert sem_coluna.status_code == 422 and "turno" in sem_coluna.text
    modelo = cliente.get("/api/dsh/importacao/perdas/modelo", headers=h)
    assert modelo.status_code == 200 and modelo.text.startswith("﻿data;turno;estacao")


# ---------------------------------------------------------------- configuração


def test_limites_do_semaforo(cliente, token_de, dsh, sessao):
    h = token_de("GES-0001")
    passagens(sessao, dsh, manaus(DIA, 10), aprovadas=96, reprovadas=4)
    assert painel(cliente, h)["indice_defeitos"]["semaforo"] == "amarelo"  # 4% entre 2 e 5

    invertido = cliente.put("/api/dsh/limites/indice_defeitos", headers=h, json={"limite_verde": 5, "limite_amarelo": 3})
    assert invertido.status_code == 422 and "menor é melhor" in invertido.text
    assert cliente.put("/api/dsh/limites/indice_defeitos", headers=h, json={"limite_verde": 4, "limite_amarelo": 8}).status_code == 200
    assert painel(cliente, h)["indice_defeitos"]["semaforo"] == "verde"
    assert cliente.put("/api/dsh/limites/indice_defeitos", headers=token_de("OPE-0001"),
                       json={"limite_verde": 4, "limite_amarelo": 8}).status_code == 403


def test_turnos_e_tipos_de_perda(cliente, token_de, dsh):
    h = token_de("GES-0001")
    sobreposto = cliente.put(f"/api/dsh/turnos/{dsh['turno'][0]}", headers=h,
                             json={"nome": "1º turno", "hora_inicio": "06:00", "hora_fim": "15:00"})
    assert sobreposto.status_code == 409
    ok = cliente.put(f"/api/dsh/turnos/{dsh['turno'][0]}", headers=h,
                     json={"nome": "1º turno", "hora_inicio": "05:00", "hora_fim": "14:00"}).json()
    assert ok["duracao_min"] == 540

    novo = cliente.post("/api/dsh/tipos-perda", headers=h, json={"nome": "Peça riscada"}).json()
    assert cliente.post("/api/dsh/tipos-perda", headers=h, json={"nome": "peca riscada"}).status_code == 409
    cliente.patch(f"/api/dsh/tipos-perda/{novo['id']}", headers=h, json={"ativo": False})
    nomes_operador = [t["nome"] for t in cliente.get("/api/dsh/opcoes", headers=token_de("OPE-0001")).json()["tipos_perda"]]
    assert "Peça riscada" not in nomes_operador
    assert cliente.get("/api/dsh/opcoes", headers=token_de("OPE-0001")).json()["permissoes"] == {"lancar": False, "configurar": False}


def test_historico_de_producao(cliente, token_de, dsh, sessao):
    passagens(sessao, dsh, manaus(DIA, 10), aprovadas=9, reprovadas=1)
    passagens(sessao, dsh, manaus(DIA + timedelta(days=1), 15), aprovadas=4, modelo=1)
    meta(sessao, dsh, 20)
    r = cliente.get("/api/dsh/historico/producao", headers=token_de("OPE-0001"),
                    params={"de": "2026-08-15", "ate": "2026-08-16"}).json()
    assert [(l["data"], l["turno"], l["modelo"], l["realizada"], l["meta"], l["atendimento_meta"]) for l in r] == [
        ("2026-08-16", "2º turno", "AMT N16", 4, 0, None),
        ("2026-08-15", "1º turno", "AMT N14", 10, 20, 50.0),
    ]
