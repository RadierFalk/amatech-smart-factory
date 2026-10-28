"""
Serviço de Relatórios e Indicadores Industriais (KPIs: Downtime, MTTR, MTTA, MTBF, Disponibilidade).
Atende ao requisito F12 e ao endpoint GET /api/manutencao/indicadores.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from config import TEMPO_PROGRAMADO_POR_MAQUINA_MIN
from database import get_db


def _parse_ts(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        limpo = str(ts_str).replace("T", " ").split(".")[0]
        return datetime.strptime(limpo, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _calcular_downtime_chamado(c: Any, agora: datetime | None = None) -> int:
    """
    Calcula o downtime efetivo (em minutos) de um chamado para o Dashboard:
    - CANCELADO: 0 min
    - CONCLUIDO: usa downtime_minutos gravado (ou calcula fim - abertura, mínimo de 1 min)
    - ABERTO / EM_ANDAMENTO: calcula o tempo decorrido desde a abertura até o instante atual (mínimo de 1 min),
      exceto preventivas programadas que ainda estão com status ABERTO e máquina OPERACIONAL.
    """
    status = c["status_chamado"]
    if status == "CANCELADO":
        return 0

    if status == "CONCLUIDO":
        gravado = c["downtime_minutos"]
        if gravado is not None and int(gravado) > 0:
            return int(gravado)
        dt_ab = _parse_ts(c["data_hora_abertura"])
        dt_fim = _parse_ts(c["data_hora_fim_atendimento"])
        if dt_ab and dt_fim and dt_fim >= dt_ab:
            return max(1, int(round((dt_fim - dt_ab).total_seconds() / 60.0)))
        return 1

    if status in ("ABERTO", "EM_ANDAMENTO"):
        chaves = c.keys() if hasattr(c, "keys") else ()
        status_eq = c["status_operacional"] if "status_operacional" in chaves else None
        if status == "ABERTO" and c["tipo_manutencao"] == "PREVENTIVA" and status_eq == "OPERACIONAL":
            return 0
        dt_ab = _parse_ts(c["data_hora_abertura"])
        if not dt_ab:
            return 0
        ref = agora or datetime.now(timezone.utc)
        segundos = max(0.0, (ref - dt_ab).total_seconds())
        return max(1, int(round(segundos / 60.0)))

    return 0


def obter_indicadores_consolidados(
    periodo_dias: int | None = None,
    setor: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Calcula os indicadores industriais de classe mundial especificados no SDD (Seção 5):
    - Downtime Total (minutos)
    - MTTR (Mean Time To Repair - minutos)
    - MTTA (Mean Time To Acknowledge / Resposta - minutos)
    - MTBF (Mean Time Between Failures - minutos/horas)
    - Disponibilidade Operacional (%)
    - Contadores de máquinas e chamados por status
    """
    filtros_chamados = []
    params_chamados: list[Any] = []

    if periodo_dias is not None and periodo_dias > 0:
        dt_corte = (datetime.now(timezone.utc) - timedelta(days=periodo_dias)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        filtros_chamados.append("c.data_hora_abertura >= ?")
        params_chamados.append(dt_corte)

    if setor and setor != "Todos":
        filtros_chamados.append("e.setor = ?")
        params_chamados.append(setor)

    where_chamados = f"WHERE {' AND '.join(filtros_chamados)}" if filtros_chamados else ""

    filtro_eq = "WHERE ativo = 1"
    params_eq: list[Any] = []
    if setor and setor != "Todos":
        filtro_eq += " AND setor = ?"
        params_eq.append(setor)

    with get_db(db_path) as conn:
        # 1. Status das Máquinas Ativas
        eq_rows = conn.execute(
            f"SELECT status_operacional, COUNT(*) AS qtd FROM equipamentos {filtro_eq} GROUP BY status_operacional",
            tuple(params_eq),
        ).fetchall()

        mapa_eq = {"OPERACIONAL": 0, "EM_MANUTENCAO": 0, "PARADA": 0}
        for r in eq_rows:
            mapa_eq[r["status_operacional"]] = int(r["qtd"])
        total_maquinas = sum(mapa_eq.values())

        # 2. Chamados no período/setor
        chamados = conn.execute(
            f"""
            SELECT
                c.id,
                c.equipamento_id,
                c.status_chamado,
                c.tipo_manutencao,
                c.prioridade,
                c.data_hora_abertura,
                c.data_hora_inicio_atendimento,
                c.data_hora_fim_atendimento,
                c.downtime_minutos,
                e.status_operacional
            FROM chamados_manutencao c
            JOIN equipamentos e ON e.id = c.equipamento_id
            {where_chamados}
            """,
            tuple(params_chamados),
        ).fetchall()

        total_chamados = len(chamados)
        chamados_abertos = sum(1 for c in chamados if c["status_chamado"] == "ABERTO")
        chamados_em_andamento = sum(1 for c in chamados if c["status_chamado"] == "EM_ANDAMENTO")
        chamados_concluidos = sum(1 for c in chamados if c["status_chamado"] == "CONCLUIDO")

        # Downtime Total Acumulado (chamados concluídos + tempo decorrido de paradas ativas)
        agora_utc = datetime.now(timezone.utc)
        downtime_concluido = sum(
            _calcular_downtime_chamado(c, agora_utc)
            for c in chamados
            if c["status_chamado"] == "CONCLUIDO"
        )
        downtime_ativo = sum(
            _calcular_downtime_chamado(c, agora_utc)
            for c in chamados
            if c["status_chamado"] in ("ABERTO", "EM_ANDAMENTO")
        )
        downtime_total = downtime_concluido + downtime_ativo

        # MTTR: Média de (fim - inicio) dos chamados concluídos (ou em andamento quando não houver concluídos)
        tempos_reparo: list[float] = []
        for c in chamados:
            if c["status_chamado"] == "CONCLUIDO":
                dt_ini = _parse_ts(c["data_hora_inicio_atendimento"])
                dt_fim = _parse_ts(c["data_hora_fim_atendimento"])
                if dt_ini and dt_fim and dt_fim >= dt_ini:
                    tempos_reparo.append(max(1.0, (dt_fim - dt_ini).total_seconds() / 60.0))
                elif c["downtime_minutos"] is not None:
                    tempos_reparo.append(float(max(1, int(c["downtime_minutos"]))))

        mttr_minutos = round(sum(tempos_reparo) / len(tempos_reparo), 1) if tempos_reparo else 0.0

        # MTTA: Média de (inicio - abertura) dos chamados concluídos (ou atendidos quando não houver concluídos)
        tempos_resposta_concluidos: list[float] = []
        tempos_resposta_todos: list[float] = []
        for c in chamados:
            dt_ab = _parse_ts(c["data_hora_abertura"])
            dt_ini = _parse_ts(c["data_hora_inicio_atendimento"])
            if dt_ab and dt_ini and dt_ini >= dt_ab:
                diff_min = max(1.0, (dt_ini - dt_ab).total_seconds() / 60.0)
                tempos_resposta_todos.append(diff_min)
                if c["status_chamado"] == "CONCLUIDO":
                    tempos_resposta_concluidos.append(diff_min)

        lista_mtta = tempos_resposta_concluidos if tempos_resposta_concluidos else tempos_resposta_todos
        mtta_minutos = round(sum(lista_mtta) / len(lista_mtta), 1) if lista_mtta else 0.0

        # Disponibilidade Geral (%) = (1 - Downtime Total / Tempo Total Programado) * 100
        tempo_total_programado = max(1, total_maquinas * TEMPO_PROGRAMADO_POR_MAQUINA_MIN)
        disponibilidade_pct = round(
            max(0.0, min(100.0, (1.0 - (downtime_total / tempo_total_programado)) * 100.0)),
            2,
        )

        # MTBF = Tempo Operacional Total / Número de Falhas Corretivas
        falhas_corretivas = sum(
            1
            for c in chamados
            if c["tipo_manutencao"] == "CORRETIVA" and c["status_chamado"] != "CANCELADO"
        )
        tempo_operacional_total = max(0, tempo_total_programado - downtime_total)
        mtbf_minutos = (
            round(tempo_operacional_total / falhas_corretivas, 1)
            if falhas_corretivas > 0
            else float(tempo_operacional_total)
        )

        return {
            "sistema": "Controle da Manutencao",
            "downtime_total_minutos": downtime_total,
            "downtime_concluido_minutos": downtime_concluido,
            "downtime_ativo_minutos": downtime_ativo,
            "mttr_minutos": mttr_minutos,
            "mtta_resposta_minutos": mtta_minutos,
            "mtbf_minutos": mtbf_minutos,
            "total_chamados": total_chamados,
            "chamados_abertos": chamados_abertos,
            "chamados_em_andamento": chamados_em_andamento,
            "chamados_concluidos": chamados_concluidos,
            "total_maquinas": total_maquinas,
            "maquinas_operacionais": mapa_eq["OPERACIONAL"],
            "maquinas_em_manutencao": mapa_eq["EM_MANUTENCAO"],
            "maquinas_paradas": mapa_eq["PARADA"],
            "disponibilidade_geral_pct": disponibilidade_pct,
        }


def obter_dados_graficos_dashboard(
    periodo_dias: int | None = None,
    setor: str | None = None,
    db_path: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Retorna as séries consolidadas para os 4 gráficos Plotly do Dashboard Gerencial (Tela 6):
    1. downtime_por_maquina: Ranking de gargalos (Downtime acumulado e nº de chamados por máquina)
    2. chamados_por_causa_raiz: Distribuição de chamados por causa raiz
    3. evolucao_diaria_paradas: Série temporal diária de paradas e downtime
    4. chamados_por_setor: Chamados agrupados por setor e status
    """
    filtros = ["c.status_chamado != 'CANCELADO'"]
    params: list[Any] = []

    if periodo_dias is not None and periodo_dias > 0:
        dt_corte = (datetime.now(timezone.utc) - timedelta(days=periodo_dias)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        filtros.append("c.data_hora_abertura >= ?")
        params.append(dt_corte)

    if setor and setor != "Todos":
        filtros.append("e.setor = ?")
        params.append(setor)

    where_clause = f"WHERE {' AND '.join(filtros)}"

    expr_downtime = """
        CASE
            WHEN c.id IS NULL OR c.status_chamado = 'CANCELADO' THEN 0
            WHEN c.status_chamado = 'ABERTO' AND c.tipo_manutencao = 'PREVENTIVA' AND e.status_operacional = 'OPERACIONAL' THEN 0
            WHEN c.downtime_minutos IS NOT NULL AND c.downtime_minutos > 0 THEN c.downtime_minutos
            WHEN c.status_chamado = 'CONCLUIDO' AND c.data_hora_fim_atendimento IS NOT NULL THEN
                MAX(1, CAST(ROUND((julianday(c.data_hora_fim_atendimento) - julianday(c.data_hora_abertura)) * 1440.0) AS INTEGER))
            WHEN c.status_chamado = 'CONCLUIDO' THEN 1
            WHEN c.status_chamado IN ('ABERTO', 'EM_ANDAMENTO') AND c.data_hora_abertura IS NOT NULL THEN
                MAX(1, CAST(ROUND((julianday('now') - julianday(c.data_hora_abertura)) * 1440.0) AS INTEGER))
            ELSE 0
        END
    """

    with get_db(db_path) as conn:
        # 1. Downtime Acumulado por Máquina (inclui tempo decorrido de paradas ativas para visão completa)
        rows_maq = conn.execute(
            f"""
            SELECT
                e.codigo_tag,
                e.nome,
                e.setor,
                COUNT(c.id) AS total_ocorrencias,
                COALESCE(SUM({expr_downtime}), 0) AS downtime_concluido_min
            FROM equipamentos e
            LEFT JOIN chamados_manutencao c
                ON c.equipamento_id = e.id AND {' AND '.join(filtros)}
            WHERE e.ativo = 1 {"AND e.setor = ?" if (setor and setor != "Todos") else ""}
            GROUP BY e.id, e.codigo_tag, e.nome, e.setor
            ORDER BY downtime_concluido_min DESC, total_ocorrencias DESC, e.codigo_tag ASC
            """,
            tuple(params + ([setor] if (setor and setor != "Todos") else [])),
        ).fetchall()

        # 2. Distribuição por Causa Raiz
        rows_causa = conn.execute(
            f"""
            SELECT
                COALESCE(NULLIF(TRIM(c.causa_raiz), ''), 'Em Diagnóstico / Aguardando Laudo') AS causa_raiz,
                COUNT(c.id) AS quantidade,
                COALESCE(SUM({expr_downtime}), 0) AS downtime_min
            FROM chamados_manutencao c
            JOIN equipamentos e ON e.id = c.equipamento_id
            {where_clause}
            GROUP BY COALESCE(NULLIF(TRIM(c.causa_raiz), ''), 'Em Diagnóstico / Aguardando Laudo')
            ORDER BY quantidade DESC
            """,
            tuple(params),
        ).fetchall()

        # 3. Evolução Diária de Paradas de Linha
        rows_diario = conn.execute(
            f"""
            SELECT
                date(c.data_hora_abertura) AS data,
                COUNT(c.id) AS total_chamados,
                COALESCE(SUM({expr_downtime}), 0) AS downtime_min
            FROM chamados_manutencao c
            JOIN equipamentos e ON e.id = c.equipamento_id
            {where_clause}
            GROUP BY date(c.data_hora_abertura)
            ORDER BY data ASC
            """,
            tuple(params),
        ).fetchall()

        # 4. Chamados por Setor e Status
        rows_setor = conn.execute(
            f"""
            SELECT
                e.setor,
                c.status_chamado,
                COUNT(c.id) AS quantidade,
                COALESCE(SUM({expr_downtime}), 0) AS downtime_min
            FROM chamados_manutencao c
            JOIN equipamentos e ON e.id = c.equipamento_id
            {where_clause}
            GROUP BY e.setor, c.status_chamado
            ORDER BY e.setor ASC
            """,
            tuple(params),
        ).fetchall()

        # 5. Downtime Consolidado por Estação/Setor (para gráfico horizontal "Downtime por estação do processo")
        rows_estacao = conn.execute(
            f"""
            SELECT
                e.setor AS estacao,
                COUNT(c.id) AS chamados,
                COALESCE(SUM({expr_downtime}), 0) AS downtime_minutos
            FROM equipamentos e
            LEFT JOIN chamados_manutencao c
                ON c.equipamento_id = e.id AND {' AND '.join(filtros)}
            WHERE e.ativo = 1 {"AND e.setor = ?" if (setor and setor != "Todos") else ""}
            GROUP BY e.setor
            ORDER BY downtime_minutos DESC, chamados DESC
            """,
            tuple(params + ([setor] if (setor and setor != "Todos") else [])),
        ).fetchall()

        # 6. Peças mais consumidas no período
        rows_pecas = conn.execute(
            f"""
            SELECT
                p.codigo_peca,
                p.nome,
                p.unidade_medida,
                COALESCE(SUM(cpt.quantidade), 0) AS quantidade
            FROM chamado_pecas_trocadas cpt
            JOIN pecas p ON p.id = cpt.peca_id
            JOIN chamados_manutencao c ON c.id = cpt.chamado_id
            JOIN equipamentos e ON e.id = c.equipamento_id
            {where_clause}
            GROUP BY p.id, p.codigo_peca, p.nome, p.unidade_medida
            ORDER BY quantidade DESC, p.codigo_peca ASC
            """,
            tuple(params),
        ).fetchall()

        return {
            "downtime_por_maquina": [dict(r) for r in rows_maq],
            "chamados_por_causa_raiz": [dict(r) for r in rows_causa],
            "evolucao_diaria_paradas": [dict(r) for r in rows_diario],
            "chamados_por_setor": [dict(r) for r in rows_setor],
            "downtime_por_estacao": [dict(r) for r in rows_estacao],
            "pecas_consumidas": [dict(r) for r in rows_pecas],
        }
