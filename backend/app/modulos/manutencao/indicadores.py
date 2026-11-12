"""Indicadores de manutenção: downtime, MTTR, MTTA, MTBF e disponibilidade (portado de relatorio_service.py).

O cálculo é feito em Python sobre os chamados do período, e não em SQL com funções de data
específicas do banco. O volume de uma fábrica (centenas de OS por mês) cabe folgado em memória.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.modulos.manutencao.constantes import (
    TEMPO_PROGRAMADO_POR_MAQUINA_MIN,
    StatusChamado,
    StatusEquipamento,
    TipoManutencao,
)
from app.modulos.manutencao.modelos import Chamado, ChamadoPeca, Equipamento

SEM_LAUDO = "Em diagnóstico / aguardando laudo"


def downtime_efetivo(chamado: Chamado, referencia: datetime) -> int:
    """Minutos de máquina parada atribuídos a um chamado.

    - Cancelado: 0.
    - Concluído: o downtime gravado (ou fim - abertura, mínimo 1).
    - Ativo: tempo desde a abertura até agora, exceto preventiva ainda não iniciada
      com a máquina funcionando (está só programada, não parou nada).
    """
    status = chamado.status_chamado
    if status == StatusChamado.CANCELADO:
        return 0
    if status == StatusChamado.CONCLUIDO:
        if chamado.downtime_minutos:
            return int(chamado.downtime_minutos)
        return tempo.minutos_entre(chamado.data_hora_abertura, chamado.data_hora_fim_atendimento) or 1
    if (
        status == StatusChamado.ABERTO
        and chamado.tipo_manutencao == TipoManutencao.PREVENTIVA
        and chamado.equipamento.status_operacional == StatusEquipamento.OPERACIONAL
    ):
        return 0
    return tempo.minutos_entre(chamado.data_hora_abertura, referencia)


def _chamados_do_periodo(sessao: Session, periodo_dias: int | None, setor: str | None) -> list[Chamado]:
    consulta = select(Chamado).join(Chamado.equipamento)
    if periodo_dias and periodo_dias > 0:
        consulta = consulta.where(Chamado.data_hora_abertura >= tempo.agora() - timedelta(days=periodo_dias))
    if setor:
        consulta = consulta.where(Equipamento.setor == setor)
    return list(sessao.scalars(consulta))


def _maquinas_ativas(sessao: Session, setor: str | None) -> list[Equipamento]:
    consulta = select(Equipamento).where(Equipamento.ativo.is_(True))
    if setor:
        consulta = consulta.where(Equipamento.setor == setor)
    return list(sessao.scalars(consulta))


def _media(valores: list[float]) -> float:
    return round(sum(valores) / len(valores), 1) if valores else 0.0


def indicadores(sessao: Session, periodo_dias: int | None = None, setor: str | None = None) -> dict[str, Any]:
    maquinas = _maquinas_ativas(sessao, setor)
    chamados = _chamados_do_periodo(sessao, periodo_dias, setor)
    tempo_programado = max(1, len(maquinas) * TEMPO_PROGRAMADO_POR_MAQUINA_MIN)
    return resumo(chamados, maquinas, tempo.agora(), tempo_programado)


def resumo(chamados: list[Chamado], maquinas: list[Equipamento], agora: datetime, tempo_programado: int) -> dict[str, Any]:
    """Indicadores de uma lista de chamados. `tempo_programado` (min) é a base da disponibilidade e do MTBF;
    o Dashboard passa o tempo de turno do período escolhido."""
    tempo_programado = max(1, tempo_programado)
    por_status_maquina = {s.value: 0 for s in StatusEquipamento}
    for m in maquinas:
        por_status_maquina[m.status_operacional] += 1

    concluidos = [c for c in chamados if c.status_chamado == StatusChamado.CONCLUIDO]
    ativos = [c for c in chamados if c.status_chamado in (StatusChamado.ABERTO, StatusChamado.EM_ANDAMENTO)]

    downtime_concluido = sum(downtime_efetivo(c, agora) for c in concluidos)
    downtime_ativo = sum(downtime_efetivo(c, agora) for c in ativos)
    downtime_total = downtime_concluido + downtime_ativo

    # MTTR: média de (fim - início do atendimento) das OS concluídas.
    reparos = [
        float(tempo.minutos_entre(c.data_hora_inicio_atendimento, c.data_hora_fim_atendimento) or c.downtime_minutos or 1)
        for c in concluidos
    ]
    # MTTA: média de (início do atendimento - abertura). Usa as concluídas; sem nenhuma, todas as atendidas.
    respostas_concluidas = [
        float(tempo.minutos_entre(c.data_hora_abertura, c.data_hora_inicio_atendimento))
        for c in concluidos
        if c.data_hora_inicio_atendimento
    ]
    respostas_todas = [
        float(tempo.minutos_entre(c.data_hora_abertura, c.data_hora_inicio_atendimento))
        for c in chamados
        if c.data_hora_inicio_atendimento
    ]

    disponibilidade = round(max(0.0, min(100.0, (1 - downtime_total / tempo_programado) * 100)), 2)

    falhas_corretivas = sum(
        1 for c in chamados if c.tipo_manutencao == TipoManutencao.CORRETIVA and c.status_chamado != StatusChamado.CANCELADO
    )
    tempo_operacional = max(0, tempo_programado - downtime_total)
    mtbf = round(tempo_operacional / falhas_corretivas, 1) if falhas_corretivas else float(tempo_operacional)

    return {
        "downtime_total_minutos": downtime_total,
        "downtime_concluido_minutos": downtime_concluido,
        "downtime_ativo_minutos": downtime_ativo,
        "mttr_minutos": _media(reparos),
        "mtta_minutos": _media(respostas_concluidas or respostas_todas),
        "mtbf_minutos": mtbf,
        "disponibilidade_pct": disponibilidade,
        "total_chamados": len(chamados),
        "chamados_abertos": sum(1 for c in chamados if c.status_chamado == StatusChamado.ABERTO),
        "chamados_em_andamento": sum(1 for c in chamados if c.status_chamado == StatusChamado.EM_ANDAMENTO),
        "chamados_concluidos": len(concluidos),
        "chamados_cancelados": sum(1 for c in chamados if c.status_chamado == StatusChamado.CANCELADO),
        "preventivas": sum(1 for c in chamados if c.tipo_manutencao == TipoManutencao.PREVENTIVA),
        "corretivas": sum(1 for c in chamados if c.tipo_manutencao == TipoManutencao.CORRETIVA),
        "total_maquinas": len(maquinas),
        "maquinas_operacionais": por_status_maquina[StatusEquipamento.OPERACIONAL],
        "maquinas_em_manutencao": por_status_maquina[StatusEquipamento.EM_MANUTENCAO],
        "maquinas_paradas": por_status_maquina[StatusEquipamento.PARADA],
    }


def graficos(sessao: Session, periodo_dias: int | None = None, setor: str | None = None) -> dict[str, list[dict[str, Any]]]:
    """Séries dos gráficos do painel de gestão. Chamados cancelados não entram."""
    agora = tempo.agora()
    maquinas = _maquinas_ativas(sessao, setor)
    chamados = [c for c in _chamados_do_periodo(sessao, periodo_dias, setor) if c.status_chamado != StatusChamado.CANCELADO]

    por_maquina: dict[int, dict[str, Any]] = {
        m.id: {"codigo_tag": m.codigo_tag, "nome": m.nome, "setor": m.setor, "chamados": 0, "downtime_minutos": 0}
        for m in maquinas
    }
    por_setor: dict[str, dict[str, Any]] = {m.setor: {"setor": m.setor, "chamados": 0, "downtime_minutos": 0} for m in maquinas}
    por_causa: dict[str, dict[str, Any]] = {}
    por_dia: dict[str, dict[str, Any]] = {}
    por_setor_status: dict[tuple[str, str], int] = defaultdict(int)

    for c in chamados:
        dt = downtime_efetivo(c, agora)
        if c.equipamento_id in por_maquina:
            por_maquina[c.equipamento_id]["chamados"] += 1
            por_maquina[c.equipamento_id]["downtime_minutos"] += dt
        if c.equipamento.ativo:
            item = por_setor.setdefault(c.equipamento.setor, {"setor": c.equipamento.setor, "chamados": 0, "downtime_minutos": 0})
            item["chamados"] += 1
            item["downtime_minutos"] += dt
        causa = (c.causa_raiz or "").strip() or SEM_LAUDO
        item = por_causa.setdefault(causa, {"causa_raiz": causa, "chamados": 0, "downtime_minutos": 0})
        item["chamados"] += 1
        item["downtime_minutos"] += dt
        dia = tempo.utc(c.data_hora_abertura).astimezone(tempo.FUSO_FABRICA).date().isoformat()
        item = por_dia.setdefault(dia, {"data": dia, "chamados": 0, "downtime_minutos": 0})
        item["chamados"] += 1
        item["downtime_minutos"] += dt
        por_setor_status[(c.equipamento.setor, c.status_chamado)] += 1

    # Peças consumidas nas OS do período (inclui máquinas inativas: a peça foi gasta do mesmo jeito).
    ids = [c.id for c in chamados]
    pecas: dict[int, dict[str, Any]] = {}
    if ids:
        for item in sessao.scalars(select(ChamadoPeca).where(ChamadoPeca.chamado_id.in_(ids))):
            p = pecas.setdefault(
                item.peca_id,
                {"codigo_peca": item.peca.codigo_peca, "nome": item.peca.nome, "unidade_medida": item.peca.unidade_medida, "quantidade": Decimal(0)},
            )
            p["quantidade"] += item.quantidade

    def ordenar(linhas, *chaves):
        return sorted(linhas, key=lambda x: tuple(-x[k] for k in chaves))

    return {
        "downtime_por_maquina": ordenar(por_maquina.values(), "downtime_minutos", "chamados"),
        "downtime_por_setor": ordenar(por_setor.values(), "downtime_minutos", "chamados"),
        "chamados_por_causa_raiz": ordenar(por_causa.values(), "chamados", "downtime_minutos"),
        "evolucao_diaria": sorted(por_dia.values(), key=lambda x: x["data"]),
        "chamados_por_setor_status": [
            {"setor": s, "status_chamado": st, "chamados": n} for (s, st), n in sorted(por_setor_status.items())
        ],
        "pecas_consumidas": sorted(
            ({**p, "quantidade": float(p["quantidade"])} for p in pecas.values()), key=lambda x: -x["quantidade"]
        ),
    }
