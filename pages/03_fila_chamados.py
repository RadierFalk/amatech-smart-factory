"""
Tela 4: Fila de Chamados Técnicos (F05, F06).
Lista os chamados com status ABERTO ordenados por prioridade (Crítica no topo) e tempo de espera,
permitindo ao Técnico ou Gestor assumir a OS com 1 clique.
"""
import pandas as pd
import streamlit as st

from config import COLORS
from services.chamado_service import (
    assumir_chamado,
    listar_chamados_em_andamento,
    listar_fila_chamados,
)
from services.equipamento_service import listar_setores
from services.relatorio_service import obter_indicadores_consolidados
from ui_components import (
    badge_prioridade_html,
    formatar_duracao_hm,
    navegar_para,
    renderizar_cabecalho,
    renderizar_kpi_card,
)


def render() -> None:
    """Renderiza a Tela 4: Fila de Chamados Técnicos."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_cabecalho(
        "📋 Fila de Chamados Técnicos (Ordens de Serviço Pendentes)",
        "Priorização automática por criticidade e maior tempo de máquina parada",
        f"Técnico: {usuario['nome']}",
    )

    ind = obter_indicadores_consolidados()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        renderizar_kpi_card(
            "Pendentes na Fila (Abertos)",
            str(ind["chamados_abertos"]),
            "Aguardando técnico assumir",
            COLORS["PARADA"],
        )
    with c2:
        renderizar_kpi_card(
            "Em Atendimento Agora",
            str(ind["chamados_em_andamento"]),
            "Máquinas em manutenção",
            COLORS["EM_MANUTENCAO"],
        )
    with c3:
        renderizar_kpi_card(
            "Concluídos no Período",
            str(ind["chamados_concluidos"]),
            "Ordens de serviço encerradas",
            COLORS["OPERACIONAL"],
        )
    with c4:
        renderizar_kpi_card(
            "MTTA (Tempo Médio Resposta)",
            f"{ind['mtta_resposta_minutos']} min",
            "Meta AMATECH: < 15 min",
            COLORS["secondary"],
        )

    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        setor_filtro = st.selectbox(
            "Filtrar Fila por Setor",
            options=["Todos"] + listar_setores(),
            index=0,
            key="filtro_setor_fila",
        )
    with col_f2:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar Fila", use_container_width=True):
            st.rerun()

    fila = listar_fila_chamados(setor=setor_filtro)

    st.subheader(f"🚨 Chamados Aguardando Atendimento ({len(fila)})")

    if not fila:
        st.success(
            "🎉 **Fila zerada!** Não há chamados pendentes aguardando atendimento neste momento."
        )
    else:
        for ch in fila:
            cor_prio = COLORS.get(ch["prioridade"], COLORS["secondary"])
            badge_prio = badge_prioridade_html(ch["prioridade"])
            tempo_espera_str = formatar_duracao_hm(ch["tempo_espera_min"])

            with st.container():
                col_info, col_acao = st.columns([4, 1.2])
                with col_info:
                    st.markdown(
                        f"""
                        <div style="background:#FFFFFF; border-left:6px solid {cor_prio}; border-radius:10px;
                                    padding:16px 20px; margin-bottom:10px; box-shadow:0 2px 6px rgba(0,0,0,0.06);">
                            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                                <div>
                                    <span style="font-size:1.15rem; font-weight:800; color:{COLORS['primary']};">
                                        OS #{ch['id']} — {ch['equipamento_tag']} ({ch['equipamento_nome']})
                                    </span>
                                    &nbsp; {badge_prio}
                                    <span style="font-size:0.78rem; background:#E2E8F0; padding:3px 8px; border-radius:6px; font-weight:600; margin-left:6px;">
                                        {ch['tipo_manutencao']}
                                    </span>
                                </div>
                                <div style="font-size:0.9rem; font-weight:700; color:{COLORS['PARADA']};">
                                    ⏱️ Tempo Parado: {tempo_espera_str}
                                </div>
                            </div>
                            <div style="font-size:0.88rem; color:#334155; margin-top:8px;">
                                <strong>Sintoma / Falha:</strong> {ch['descricao_falha']}
                            </div>
                            <div style="font-size:0.8rem; color:#64748B; margin-top:6px;">
                                📍 Setor: <strong>{ch['setor']}</strong> ({ch['posto_trabalho'] or 'Posto 01'})
                                &nbsp;|&nbsp; 👤 Solicitante: <strong>{ch['operador_nome']}</strong> ({ch['operador_matricula']})
                                &nbsp;|&nbsp; 🕒 Abertura (UTC): <strong>{ch['data_hora_abertura']}</strong>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with col_acao:
                    st.write("")
                    if st.button(
                        f"🛠️ Assumir OS #{ch['id']}",
                        key=f"btn_assumir_{ch['id']}",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            assumir_chamado(chamado_id=ch["id"], tecnico_id=usuario["id"])
                            st.toast(
                                f"OS #{ch['id']} assumida com sucesso! Máquina em manutenção.",
                                icon="🔧",
                            )
                            navegar_para("ordem_servico", os_selecionada_id=ch["id"])
                        except Exception as exc:
                            st.error(f"Erro ao assumir OS #{ch['id']}: {exc}")

        # Tabela resumo consolidada conforme especificação da Tela 4
        with st.expander("📊 Visualizar Fila em Formato de Tabela Consolidada", expanded=False):
            df_fila = pd.DataFrame(fila)[
                [
                    "id",
                    "equipamento_tag",
                    "equipamento_nome",
                    "setor",
                    "prioridade",
                    "data_hora_abertura",
                    "tempo_espera_min",
                    "operador_nome",
                    "descricao_falha",
                ]
            ].rename(
                columns={
                    "id": "Nº OS",
                    "equipamento_tag": "Tag",
                    "equipamento_nome": "Máquina",
                    "setor": "Setor",
                    "prioridade": "Prioridade",
                    "data_hora_abertura": "Data/Hora Abertura",
                    "tempo_espera_min": "Tempo Parado (min)",
                    "operador_nome": "Operador Solicitante",
                    "descricao_falha": "Descrição da Falha",
                }
            )
            st.dataframe(df_fila, use_container_width=True, hide_index=True)

    st.divider()

    # Seção rápida de OS já em andamento para acesso direto
    em_andamento = listar_chamados_em_andamento()
    st.subheader(f"🔧 Ordens de Serviço em Atendimento ({len(em_andamento)})")
    if not em_andamento:
        st.caption("Nenhuma Ordem de Serviço em andamento neste momento.")
    else:
        for os_at in em_andamento:
            c_a, c_b = st.columns([4, 1.2])
            with c_a:
                st.info(
                    f"**OS #{os_at['id']} — {os_at['equipamento_tag']} ({os_at['equipamento_nome']})** | "
                    f"Técnico: **{os_at['tecnico_nome']}** | "
                    f"Tempo em reparo: **{formatar_duracao_hm(os_at['tempo_atendimento_min'])}**"
                )
            with c_b:
                if st.button(
                    f"Abrir OS #{os_at['id']}",
                    key=f"btn_ir_os_{os_at['id']}",
                    use_container_width=True,
                ):
                    navegar_para("ordem_servico", os_selecionada_id=os_at["id"])


if __name__ == "__main__":
    render()
