"""
Tela de Dashboard Gerencial (F12, RF10).
Replica integralmente os 4 KPIs, os 4 gráficos (Downtime por estação, Chamados por status em rosca,
Evolução diária combo barra+linha em duplo eixo e Causas raiz em roxo #6B3F8A)
e as 2 tabelas inferiores (Ranking de máquinas e Peças mais consumidas) do projeto amatech-manutencao.
"""
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import COLORS
from services.chamado_service import listar_historico_chamados
from services.relatorio_service import (
    obter_dados_graficos_dashboard,
    obter_indicadores_consolidados,
)
from ui_components import (
    esc,
    formatar_duracao_hm,
    kpi_html,
    renderizar_topbar,
    rotulo_amigavel,
)


def _layout_padrao_grafico(altura: int = 265) -> dict:
    return dict(
        font=dict(family='"Segoe UI", Roboto, Arial, sans-serif', size=12, color="#495665"),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=10, r=16, t=12, b=16),
        height=altura,
    )


def render() -> None:
    """Renderiza o Dashboard Gerencial idêntico ao A.renderDashboard do telas-gestor.js."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_topbar("Dashboard gerencial", "Indicadores de manutenção consolidados")

    # Barra de período + resumo + botões CSV e Atualizar
    c_per, c_res, c_csv, c_atu = st.columns([1.2, 2.2, 1.0, 0.8])
    with c_per:
        opcoes_dias = [
            (7, "Últimos 7 dias"),
            (30, "Últimos 30 dias"),
            (90, "Últimos 90 dias"),
            (180, "Últimos 180 dias"),
        ]
        dias_sel = st.selectbox(
            "Período",
            options=[x[0] for x in opcoes_dias],
            index=1,
            format_func=lambda d: dict(opcoes_dias)[d],
            label_visibility="collapsed",
            key="dash_dias_sel",
        )

    ind = obter_indicadores_consolidados(periodo_dias=dias_sel)
    series = obter_dados_graficos_dashboard(periodo_dias=dias_sel)

    dt_fim = datetime.now()
    dt_ini = dt_fim - timedelta(days=dias_sel)

    with c_res:
        st.markdown(
            f'<div style="padding-top:8px; font-size:12.5px; color:var(--cinza-500);">'
            f'<strong>Período:</strong> {dt_ini.strftime("%d/%m/%Y")} a {dt_fim.strftime("%d/%m/%Y")} '
            f'· {ind["total_chamados"]} chamados no período</div>',
            unsafe_allow_html=True,
        )
    with c_csv:
        registros_csv = listar_historico_chamados()
        df_exp = pd.DataFrame(registros_csv) if registros_csv else pd.DataFrame()
        csv_bytes = df_exp.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            "⤓ Exportar CSV",
            data=csv_bytes,
            file_name=f"historico_manutencao_{dt_fim.strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c_atu:
        if st.button("↻ Atualizar", type="primary", use_container_width=True):
            st.rerun()

    # 1. Os 4 KPIs Superiores (grid-4)
    downtime_min = int(ind["downtime_total_minutos"] or 0)
    downtime_horas = round(downtime_min / 60.0, 1)
    mtbf_horas = round((ind.get("mtbf_minutos") or 0) / 60.0, 1)

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            kpi_html(
                "Downtime acumulado",
                f"{downtime_horas:g}",
                unidade="h",
                detalhe=f"{downtime_min:,}".replace(",", ".") + " minutos no período",
                variante="vermelho",
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_html(
                "MTTR · tempo médio de reparo",
                f"{ind['mttr_minutos']:g}",
                unidade="min",
                detalhe=f"Resposta média: {ind['mtta_resposta_minutos']:g} min",
                variante="azul",
            ),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_html(
                "Disponibilidade das máquinas",
                f"{ind['disponibilidade_geral_pct']:g}",
                unidade="%",
                detalhe=f"MTBF: {mtbf_horas:g} h entre falhas",
                variante="verde",
            ),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            kpi_html(
                "Chamados no período",
                str(ind["total_chamados"]),
                detalhe=(
                    f"{ind['chamados_concluidos']} concluídos · "
                    f"{ind['chamados_abertos']} abertos · "
                    f"{ind['chamados_em_andamento']} em andamento"
                ),
                variante="amarelo",
            ),
            unsafe_allow_html=True,
        )

    # 2. Linha 1 de Gráficos (grid-2-1: Downtime por estação + Chamados por status)
    r1_esq, r1_dir = st.columns([2, 1])

    with r1_esq:
        st.markdown(
            """
            <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
              <div class="card-cabecalho">
                <h2>Downtime por estação do processo</h2>
                <div class="acao">minutos parados</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        estacoes = series.get("downtime_por_estacao") or []
        estacoes_rev = list(reversed(estacoes))
        cores_barras = [
            COLORS["vermelho"]
            if e["downtime_minutos"] > 800
            else (COLORS["amarelo"] if e["downtime_minutos"] > 400 else COLORS["azul"])
            for e in estacoes_rev
        ]
        fig_est = go.Figure(
            go.Bar(
                x=[e["downtime_minutos"] for e in estacoes_rev],
                y=[e["estacao"] for e in estacoes_rev],
                orientation="h",
                marker=dict(color=cores_barras, cornerradius=4),
                customdata=[e["chamados"] for e in estacoes_rev],
                hovertemplate="<b>%{y}</b><br>Downtime: %{x} min<br>%{customdata} chamado(s)<extra></extra>",
            )
        )
        layout_est = _layout_padrao_grafico(265)
        layout_est.update(
            xaxis=dict(
                title="minutos",
                gridcolor="#EEF2F6",
                zeroline=False,
            ),
            yaxis=dict(showgrid=False),
            showlegend=False,
        )
        fig_est.update_layout(**layout_est)
        st.plotly_chart(fig_est, use_container_width=True, config={"displayModeBar": False})

    with r1_dir:
        st.markdown(
            """
            <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
              <div class="card-cabecalho"><h2>Chamados por status</h2></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        mapa_status = {
            "CONCLUIDO": (ind["chamados_concluidos"], COLORS["verde"]),
            "ABERTO": (ind["chamados_abertos"], COLORS["vermelho"]),
            "EM_ANDAMENTO": (ind["chamados_em_andamento"], COLORS["amarelo"]),
        }
        labels_st = [rotulo_amigavel(k) for k in mapa_status.keys()]
        vals_st = [v[0] for v in mapa_status.values()]
        cors_st = [v[1] for v in mapa_status.values()]

        fig_status = go.Figure(
            go.Pie(
                labels=labels_st,
                values=vals_st,
                hole=0.58,
                marker=dict(colors=cors_st, line=dict(color="#FFFFFF", width=2)),
                textinfo="percent+value",
            )
        )
        layout_st = _layout_padrao_grafico(265)
        layout_st.update(
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
        )
        fig_status.update_layout(**layout_st)
        st.plotly_chart(fig_status, use_container_width=True, config={"displayModeBar": False})

    # 3. Linha 2 de Gráficos (grid-2-1: Evolução diária combo + Causas raiz em roxo)
    r2_esq, r2_dir = st.columns([2, 1])

    with r2_esq:
        st.markdown(
            """
            <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
              <div class="card-cabecalho"><h2>Evolução diária — chamados e downtime</h2></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        diario = series.get("evolucao_diaria_paradas") or []
        datas_fmt = []
        for d in diario:
            partes = str(d["data"]).split("-")
            datas_fmt.append(f"{partes[2]}/{partes[1]}" if len(partes) == 3 else str(d["data"]))

        fig_serie = go.Figure()
        fig_serie.add_trace(
            go.Bar(
                name="Downtime (min)",
                x=datas_fmt,
                y=[d["downtime_min"] for d in diario],
                marker=dict(color="rgba(46,117,182,0.55)", cornerradius=3),
                yaxis="y",
            )
        )
        fig_serie.add_trace(
            go.Scatter(
                name="Chamados abertos",
                x=datas_fmt,
                y=[d["total_chamados"] for d in diario],
                mode="lines+markers",
                line=dict(color=COLORS["vermelho"], width=2, shape="spline"),
                marker=dict(size=6, color=COLORS["vermelho"]),
                yaxis="y2",
            )
        )
        layout_ser = _layout_padrao_grafico(300)
        layout_ser.update(
            xaxis=dict(showgrid=False),
            yaxis=dict(title="min", side="left", gridcolor="#EEF2F6", zeroline=False),
            yaxis2=dict(title="chamados", side="right", overlaying="y", showgrid=False, zeroline=False),
            legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
        )
        fig_serie.update_layout(**layout_ser)
        st.plotly_chart(fig_serie, use_container_width=True, config={"displayModeBar": False})

    with r2_dir:
        st.markdown(
            """
            <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
              <div class="card-cabecalho"><h2>Causas raiz mais frequentes</h2></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        causas = series.get("chamados_por_causa_raiz") or []
        causas_rev = list(reversed(causas[:10]))
        labels_causa = [
            (c["causa_raiz"][:24] + "…") if len(c["causa_raiz"]) > 26 else c["causa_raiz"]
            for c in causas_rev
        ]
        fig_causas = go.Figure(
            go.Bar(
                x=[c["quantidade"] for c in causas_rev],
                y=labels_causa,
                orientation="h",
                marker=dict(color=COLORS["roxo"], cornerradius=4),
                hovertemplate="<b>%{y}</b><br>Ocorrências: %{x}<extra></extra>",
            )
        )
        layout_cau = _layout_padrao_grafico(300)
        layout_cau.update(
            xaxis=dict(gridcolor="#EEF2F6", dtick=1, zeroline=False),
            yaxis=dict(showgrid=False, tickfont=dict(size=10.5)),
            showlegend=False,
        )
        fig_causas.update_layout(**layout_cau)
        st.plotly_chart(fig_causas, use_container_width=True, config={"displayModeBar": False})

    # 4. Linha 3: Ranking de máquinas com mais downtime + Peças mais consumidas (grid-2)
    r3_esq, r3_dir = st.columns(2)

    with r3_esq:
        ranking = [m for m in (series.get("downtime_por_maquina") or []) if m["total_ocorrencias"] > 0]
        if not ranking:
            ranking = series.get("downtime_por_maquina") or []

        linhas_rk = "".join(
            f"""
            <tr>
              <td>{i + 1}º</td>
              <td><span class="mono"><strong>{esc(m['codigo_tag'])}</strong></span> — {esc(m['nome'])}</td>
              <td>{esc(m['setor'])}</td>
              <td class="num">{m['total_ocorrencias']}</td>
              <td class="num"><strong>{esc(formatar_duracao_hm(m['downtime_concluido_min']))}</strong></td>
            </tr>
            """
            for i, m in enumerate(ranking[:10])
        )
        if not linhas_rk:
            linhas_rk = '<tr><td colspan="5"><div class="vazio">Sem dados no período.</div></td></tr>'

        st.markdown(
            f"""
            <div class="card" style="margin-top:8px;">
              <div class="card-cabecalho"><h2>Ranking de máquinas com mais downtime</h2></div>
              <div class="tabela-wrap">
                <table class="tabela">
                  <thead>
                    <tr><th>#</th><th>Máquina</th><th>Estação</th><th class="num">Chamados</th><th class="num">Downtime</th></tr>
                  </thead>
                  <tbody>{linhas_rk}</tbody>
                </table>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with r3_dir:
        pecas_cons = series.get("pecas_consumidas") or []
        linhas_pc = "".join(
            f"""
            <tr>
              <td class="mono"><strong>{esc(p['codigo_peca'])}</strong></td>
              <td>{esc(p['nome'])}</td>
              <td class="num"><strong>{p['quantidade']:g}</strong></td>
            </tr>
            """
            for p in pecas_cons[:10]
        )
        if not linhas_pc:
            linhas_pc = '<tr><td colspan="3"><div class="vazio">Nenhuma peça trocada no período.</div></td></tr>'

        st.markdown(
            f"""
            <div class="card" style="margin-top:8px;">
              <div class="card-cabecalho"><h2>Peças mais consumidas</h2></div>
              <div class="tabela-wrap">
                <table class="tabela">
                  <thead>
                    <tr><th>Código</th><th>Peça</th><th class="num">Quantidade</th></tr>
                  </thead>
                  <tbody>{linhas_pc}</tbody>
                </table>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    render()
