"""
Tela 6: Dashboard Gerencial de KPIs (F12, RF10).
Exibe cards de Downtime Total, MTTR, MTTA, MTBF e Disponibilidade (%),
além dos 4 gráficos interativos Plotly especificados no SDD e Design System.
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from config import COLORS
from services.equipamento_service import listar_setores
from services.relatorio_service import (
    obter_dados_graficos_dashboard,
    obter_indicadores_consolidados,
)
from ui_components import formatar_duracao_hm, renderizar_cabecalho, renderizar_kpi_card


def render() -> None:
    """Renderiza a Tela 6: Dashboard Gerencial de Indicadores Industriais."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_cabecalho(
        "📊 Dashboard Gerencial de KPIs — Manutenção Industrial",
        "Indicadores de Classe Mundial: Downtime Acumulado, MTTR, MTTA, MTBF e Disponibilidade Operacional",
        f"Gestão: {usuario['nome']}",
    )

    # Filtros de Período e Setor (Especificação Tela 6)
    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        opcoes_periodo = [
            ("Todo o Histórico", None),
            ("Hoje (Últimas 24h)", 1),
            ("Últimos 7 Dias", 7),
            ("Mês Atual (Últimos 30 Dias)", 30),
        ]
        periodo_sel = st.selectbox(
            "Período de Análise",
            options=opcoes_periodo,
            format_func=lambda x: x[0],
            index=0,
            key="dash_periodo",
        )
    with col_f2:
        setor_sel = st.selectbox(
            "Setor Fabril",
            options=["Todos"] + listar_setores(),
            index=0,
            key="dash_setor",
        )
    with col_f3:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar KPIs", use_container_width=True):
            st.rerun()

    dias_filtro = periodo_sel[1]
    ind = obter_indicadores_consolidados(periodo_dias=dias_filtro, setor=setor_sel)
    series = obter_dados_graficos_dashboard(periodo_dias=dias_filtro, setor=setor_sel)

    # 1. Cards de Métricas Principais (KPIs Obrigatórios)
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        renderizar_kpi_card(
            "Downtime Total Acumulado",
            f"{ind['downtime_total_minutos']} min",
            f"Equivalente a {formatar_duracao_hm(ind['downtime_total_minutos'])} de linha parada",
            COLORS["PARADA"],
        )
    with k2:
        renderizar_kpi_card(
            "MTTR (Tempo Médio de Reparo)",
            f"{ind['mttr_minutos']:.1f} min",
            f"Base: {ind['chamados_concluidos']} OS concluída(s)",
            COLORS["EM_MANUTENCAO"],
        )
    with k3:
        renderizar_kpi_card(
            "MTTA (Tempo Médio de Resposta)",
            f"{ind['mtta_resposta_minutos']:.1f} min",
            "Tempo entre abertura e início técnico",
            COLORS["secondary"],
        )
    with k4:
        renderizar_kpi_card(
            "Disponibilidade Geral (%)",
            f"{ind['disponibilidade_geral_pct']:.2f}%",
            f"MTBF Estimado: {formatar_duracao_hm(ind['mtbf_minutos'])}",
            COLORS["OPERACIONAL"],
        )

    # Faixa secundária de resumo operacional
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Total de Chamados", ind["total_chamados"])
    s2.metric("OS Abertas (Fila)", ind["chamados_abertos"])
    s3.metric("OS em Atendimento", ind["chamados_em_andamento"])
    s4.metric("OS Concluídas", ind["chamados_concluidos"])
    s5.metric("Máquinas Operacionais", ind["maquinas_operacionais"])
    s6.metric("Máquinas Paradas/Manut.", ind["maquinas_paradas"] + ind["maquinas_em_manutencao"])

    st.divider()

    # 2. Gráficos Interativos Plotly (2x2 Grid)
    g_col1, g_col2 = st.columns(2)

    # Gráfico 1: Barras - Downtime Acumulado por Máquina (Ranking de Gargalos)
    with g_col1:
        st.subheader("1. Downtime Acumulado por Máquina (Gargalos)")
        df_maq = pd.DataFrame(series["downtime_por_maquina"])
        if df_maq.empty:
            st.info("Sem dados de máquinas para o filtro selecionado.")
        else:
            df_maq["rotulo"] = df_maq["codigo_tag"] + " (" + df_maq["nome"].str.slice(0, 22) + ")"
            fig_maq = px.bar(
                df_maq,
                x="downtime_concluido_min",
                y="rotulo",
                orientation="h",
                color="total_ocorrencias",
                text="downtime_concluido_min",
                color_continuous_scale=["#2E75B6", "#F2B705", "#D32F2F"],
                labels={
                    "downtime_concluido_min": "Downtime Acumulado (min)",
                    "rotulo": "Equipamento",
                    "total_ocorrencias": "Nº Chamados",
                },
            )
            fig_maq.update_traces(texttemplate="%{text} min", textposition="outside")
            fig_maq.update_layout(
                yaxis={"categoryorder": "total ascending"},
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                margin=dict(l=10, r=30, t=20, b=20),
                height=360,
            )
            st.plotly_chart(fig_maq, use_container_width=True)

    # Gráfico 2: Pizza / Rosca - Distribuição de Chamados por Causa Raiz
    with g_col2:
        st.subheader("2. Distribuição de Chamados por Causa Raiz")
        df_causa = pd.DataFrame(series["chamados_por_causa_raiz"])
        if df_causa.empty:
            st.info("Sem chamados registrados para análise de causa raiz.")
        else:
            fig_causa = px.pie(
                df_causa,
                names="causa_raiz",
                values="quantidade",
                hole=0.45,
                color_discrete_sequence=[
                    COLORS["primary"],
                    COLORS["secondary"],
                    COLORS["EM_MANUTENCAO"],
                    COLORS["PARADA"],
                    COLORS["OPERACIONAL"],
                    "#64748B",
                ],
            )
            fig_causa.update_traces(textinfo="percent+value")
            fig_causa.update_layout(
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                margin=dict(l=10, r=10, t=20, b=20),
                height=360,
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_causa, use_container_width=True)

    g_col3, g_col4 = st.columns(2)

    # Gráfico 3: Linhas - Evolução Diária de Paradas de Linha
    with g_col3:
        st.subheader("3. Evolução Diária de Paradas e Downtime")
        df_diario = pd.DataFrame(series["evolucao_diaria_paradas"])
        if df_diario.empty:
            st.info("Sem histórico diário para o período selecionado.")
        else:
            fig_diario = px.line(
                df_diario,
                x="data",
                y=["total_chamados", "downtime_min"],
                markers=True,
                color_discrete_map={
                    "total_chamados": COLORS["primary"],
                    "downtime_min": COLORS["PARADA"],
                },
                labels={
                    "data": "Data",
                    "value": "Quantidade / Minutos",
                    "variable": "Indicador",
                },
            )
            fig_diario.update_layout(
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                margin=dict(l=10, r=20, t=20, b=20),
                height=350,
            )
            st.plotly_chart(fig_diario, use_container_width=True)

    # Gráfico 4: Barras Empilhadas - Chamados por Setor e Status
    with g_col4:
        st.subheader("4. Chamados por Setor Produtivo e Status")
        df_setor = pd.DataFrame(series["chamados_por_setor"])
        if df_setor.empty:
            st.info("Sem chamados por setor para o filtro selecionado.")
        else:
            fig_setor = px.bar(
                df_setor,
                x="setor",
                y="quantidade",
                color="status_chamado",
                barmode="stack",
                text="quantidade",
                color_discrete_map={
                    "ABERTO": COLORS["PARADA"],
                    "EM_ANDAMENTO": COLORS["EM_MANUTENCAO"],
                    "CONCLUIDO": COLORS["OPERACIONAL"],
                },
                labels={
                    "setor": "Setor Produtivo",
                    "quantidade": "Nº de Chamados",
                    "status_chamado": "Status da OS",
                },
            )
            fig_setor.update_layout(
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                margin=dict(l=10, r=20, t=20, b=20),
                height=350,
            )
            st.plotly_chart(fig_setor, use_container_width=True)


if __name__ == "__main__":
    render()
