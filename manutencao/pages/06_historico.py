"""
Telas de Histórico de Intervenções (F11) e Auditoria de Status (F17 / RN08).
Replica os cards de filtros 3x3, tabelas .tabela com faixas de prioridade,
selos coloridos e exportação CSV do projeto amatech-manutencao.
"""
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st

from config import TIPOS_MANUTENCAO
from services.auth_service import listar_usuarios
from services.chamado_service import (
    listar_historico_auditoria,
    listar_historico_chamados,
)
from services.equipamento_service import listar_equipamentos, listar_setores
from ui_components import (
    esc,
    formatar_data_br,
    formatar_duracao_curta,
    navegar_para,
    renderizar_topbar,
    rotulo_amigavel,
    selo_html,
)


def _calc_min(t1: str | None, t2: str | None) -> int | None:
    if not t1 or not t2:
        return None
    try:
        a = datetime.strptime(str(t1).replace("T", " ").split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        b = datetime.strptime(str(t2).replace("T", " ").split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return max(0, int(round((b - a).total_seconds() / 60.0)))
    except Exception:
        return None


def render_auditoria() -> None:
    """Renderiza a tela de Auditoria de Status (A.renderAuditoria do telas-gestor.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_topbar(
        "Auditoria de status",
        "Trilha de todas as mudanças de estado das máquinas (RN08)",
    )

    auditoria = listar_historico_auditoria(limite=250)

    linhas_aud = ""
    for r in auditoria:
        os_str = f"#{r['chamado_id']}" if r.get("chamado_id") else "—"
        obs_str = (
            f"OS #{r['chamado_id']} · transição para {rotulo_amigavel(r['status_novo'])}"
            if r.get("chamado_id")
            else "Alteração operacional"
        )
        linhas_aud += (
            f'<tr>'
            f'<td>{esc(formatar_data_br(r["alterado_em"]))}</td>'
            f'<td><strong>{esc(r["equipamento_tag"])}</strong> — {esc(r["equipamento_nome"])}</td>'
            f'<td class="mono">{esc(os_str)}</td>'
            f'<td>{selo_html(r["status_anterior"])}</td>'
            f'<td>{selo_html(r["status_novo"])}</td>'
            f'<td>{esc(r["usuario_nome"])}</td>'
            f'<td>{esc(obs_str)}</td>'
            f'</tr>'
        )

    if not linhas_aud:
        linhas_aud = '<tr><td colspan="7"><div class="vazio">Nenhum evento registrado.</div></td></tr>'

    st.markdown(
        f"""
        <div class="card">
          <div class="card-cabecalho">
            <h2>Eventos registrados</h2>
            <div class="acao">{len(auditoria)} evento(s)</div>
          </div>
          <div class="tabela-wrap">
            <table class="tabela">
              <thead>
                <tr>
                  <th>Data / hora</th><th>Máquina</th><th>OS</th><th>De</th><th>Para</th><th>Usuário</th><th>Observação</th>
                </tr>
              </thead>
              <tbody>{linhas_aud}</tbody>
            </table>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    """Renderiza a tela de Histórico de Intervenções (A.renderHistorico do telas-gestor.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_topbar(
        "Histórico de intervenções",
        "Consulta filtrável e exportação dos registros",
    )

    equipamentos = listar_equipamentos(apenas_ativos=False)
    usuarios_tec = [
        u for u in listar_usuarios(apenas_ativos=False) if u["perfil"] in ("TECNICO", "GESTOR")
    ]
    setores = ["Todas"] + listar_setores()

    st.markdown(
        """
        <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
          <div class="card-cabecalho"><h2>Filtros</h2></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Grade 3x3 de filtros idêntica ao A.renderHistorico
    f1, f2, f3 = st.columns(3)
    with f1:
        dt_ini = st.date_input(
            "Data inicial",
            value=(datetime.now() - timedelta(days=30)).date(),
            key="hist_dt_ini",
        )
    with f2:
        dt_fim = st.date_input(
            "Data final",
            value=datetime.now().date(),
            key="hist_dt_fim",
        )
    with f3:
        opcoes_eq = [(None, "Todas")] + [
            (e["id"], f"{e['codigo_tag']} — {e['nome']}") for e in equipamentos
        ]
        eq_sel = st.selectbox(
            "Máquina",
            options=opcoes_eq,
            format_func=lambda x: x[1],
            key="hist_maq_sel",
        )

    f4, f5, f6 = st.columns(3)
    with f4:
        est_sel = st.selectbox("Estação", options=setores, key="hist_est_sel")
    with f5:
        opcoes_tec = [(None, "Todos")] + [(u["id"], u["nome"]) for u in usuarios_tec]
        tec_sel = st.selectbox(
            "Técnico",
            options=opcoes_tec,
            format_func=lambda x: x[1],
            key="hist_tec_sel",
        )
    with f6:
        tipo_sel = st.selectbox(
            "Tipo",
            options=["Todos"] + TIPOS_MANUTENCAO,
            format_func=lambda x: "Todos" if x == "Todos" else rotulo_amigavel(x),
            key="hist_tipo_sel",
        )

    f7, f8, f9 = st.columns([1, 1.3, 0.7])
    with f7:
        status_sel = st.selectbox(
            "Status",
            options=["Todos", "ABERTO", "EM_ANDAMENTO", "CONCLUIDO", "CANCELADO"],
            format_func=lambda x: "Todos" if x == "Todos" else rotulo_amigavel(x),
            key="hist_status_sel",
        )
    with f8:
        busca_q = st.text_input(
            "Busca livre",
            placeholder="Falha, TAG, diagnóstico…",
            key="hist_busca_q",
        )
    with f9:
        st.write("")
        st.write("")
        aplicar_periodo = st.checkbox("Filtrar datas", value=False, key="hist_use_dates")

    registros = listar_historico_chamados(
        equipamento_id=eq_sel[0],
        tecnico_id=tec_sel[0],
        setor="Todos" if est_sel == "Todas" else est_sel,
        status_chamado=status_sel,
        tipo_manutencao=tipo_sel,
        data_inicio=dt_ini.strftime("%Y-%m-%d") if aplicar_periodo else None,
        data_fim=dt_fim.strftime("%Y-%m-%d") if aplicar_periodo else None,
        busca_texto=busca_q,
    )

    col_tot, col_exp = st.columns([3.5, 1])
    with col_exp:
        if registros:
            df_csv = pd.DataFrame(registros)[
                [
                    "id",
                    "data_hora_abertura",
                    "equipamento_tag",
                    "equipamento_nome",
                    "setor",
                    "prioridade",
                    "tipo_manutencao",
                    "status_chamado",
                    "tecnico_nome",
                    "downtime_minutos",
                    "causa_raiz",
                    "descricao_falha",
                    "diagnostico_tecnico",
                    "resumo_pecas",
                ]
            ]
            csv_bytes = df_csv.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button(
                "⤓ Exportar CSV",
                data=csv_bytes,
                file_name=f"historico_intervencoes_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    linhas_hist = ""
    for r in registros[:300]:
        prio_cls = f"prioridade-{str(r['prioridade']).lower()}"
        espera_m = _calc_min(r.get("data_hora_abertura"), r.get("data_hora_inicio_atendimento"))
        reparo_m = _calc_min(r.get("data_hora_inicio_atendimento"), r.get("data_hora_fim_atendimento"))
        esp_str = formatar_duracao_curta(espera_m) if espera_m is not None else "—"
        rep_str = formatar_duracao_curta(reparo_m) if reparo_m is not None else "—"
        dt_val = (
            r["downtime_minutos"]
            if r.get("downtime_minutos") is not None
            else r.get("tempo_parado_min")
        )
        dt_str = (
            formatar_duracao_curta(dt_val)
            if dt_val is not None
            else "—"
        )
        linhas_hist += (
            f'<tr class="{prio_cls}">'
            f'<td class="mono"><strong>#{r["id"]}</strong></td>'
            f'<td>{esc(formatar_data_br(r["data_hora_abertura"]))}</td>'
            f'<td><strong>{esc(r["equipamento_tag"])}</strong></td>'
            f'<td>{esc(r["setor"])}</td>'
            f'<td>{selo_html(r["prioridade"])}</td>'
            f'<td>{selo_html(r["tipo_manutencao"])}</td>'
            f'<td>{selo_html(r["status_chamado"])}</td>'
            f'<td>{esc(r.get("tecnico_nome") or "—")}</td>'
            f'<td class="num">{esc(esp_str)}</td>'
            f'<td class="num">{esc(rep_str)}</td>'
            f'<td class="num"><strong>{esc(dt_str)}</strong></td>'
            f'<td>{esc(r.get("causa_raiz") or "—")}</td>'
            f'</tr>'
        )

    if not linhas_hist:
        linhas_hist = (
            '<tr><td colspan="12"><div class="vazio"><strong>Nenhum registro encontrado</strong>'
            "Ajuste o período ou os filtros.</div></td></tr>"
        )

    st.markdown(
        f"""
        <div class="card" style="margin-top:8px;">
          <div class="card-cabecalho">
            <h2>Registros</h2>
            <div class="acao">{len(registros)} registro(s)</div>
          </div>
          <div class="tabela-wrap">
            <table class="tabela">
              <thead>
                <tr>
                  <th>OS</th><th>Abertura</th><th>Máquina</th><th>Estação</th><th>Prioridade</th>
                  <th>Tipo</th><th>Status</th><th>Técnico</th><th class="num">Espera</th>
                  <th class="num">Reparo</th><th class="num">Downtime</th><th>Causa raiz</th>
                </tr>
              </thead>
              <tbody>{linhas_hist}</tbody>
            </table>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render()
