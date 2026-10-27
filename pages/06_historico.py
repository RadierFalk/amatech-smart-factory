"""
Tela 7: Histórico de Intervenções e Auditoria (F11, F17, RN08).
Permite filtragem avançada por máquina, técnico, setor, status, tipo, período e busca textual,
exportação em 1 clique para CSV e consulta à trilha de auditoria (historico_status).
"""
from datetime import datetime
import pandas as pd
import streamlit as st

from config import PRIORIDADES, TIPOS_MANUTENCAO
from services.auth_service import listar_usuarios
from services.chamado_service import (
    listar_historico_auditoria,
    listar_historico_chamados,
)
from services.equipamento_service import listar_equipamentos, listar_setores
from ui_components import renderizar_cabecalho


def render() -> None:
    """Renderiza a Tela 7: Histórico de Intervenções e Trilha de Auditoria."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_cabecalho(
        "📜 Histórico de Manutenção e Trilha de Auditoria",
        "Rastreabilidade completa de Ordens de Serviço, tempos de parada, peças trocadas e transições de status",
        f"Usuário: {usuario['nome']}",
    )

    aba_os, aba_auditoria = st.tabs(
        [
            "📋 Histórico de Ordens de Serviço (F11)",
            "🛡️ Trilha de Auditoria de Status - RN08 (F17)",
        ]
    )

    with aba_os:
        equipamentos = listar_equipamentos(apenas_ativos=False)
        usuarios_tec = [
            u for u in listar_usuarios(apenas_ativos=False) if u["perfil"] in ("TECNICO", "GESTOR")
        ]
        setores = ["Todos"] + listar_setores()

        with st.expander("🔍 Painel de Filtros Avançados", expanded=True):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                opcoes_eq = [(None, "Todas as Máquinas")] + [
                    (e["id"], f"{e['codigo_tag']} — {e['nome']}") for e in equipamentos
                ]
                eq_filtro = st.selectbox(
                    "Máquina / Equipamento",
                    options=opcoes_eq,
                    format_func=lambda x: x[1],
                    key="hist_eq",
                )
            with f2:
                opcoes_tec = [(None, "Todos os Técnicos")] + [
                    (u["id"], f"{u['nome']} ({u['matricula']})") for u in usuarios_tec
                ]
                tec_filtro = st.selectbox(
                    "Técnico Responsável",
                    options=opcoes_tec,
                    format_func=lambda x: x[1],
                    key="hist_tec",
                )
            with f3:
                setor_filtro = st.selectbox("Setor", options=setores, key="hist_setor")
            with f4:
                status_filtro = st.selectbox(
                    "Status da OS",
                    options=["Todos", "ABERTO", "EM_ANDAMENTO", "CONCLUIDO", "CANCELADO"],
                    key="hist_status",
                )

            f5, f6, f7, f8 = st.columns([1.2, 1.2, 1.4, 2.2])
            with f5:
                tipo_filtro = st.selectbox(
                    "Tipo de Manutenção",
                    options=["Todos"] + TIPOS_MANUTENCAO,
                    key="hist_tipo",
                )
            with f6:
                prio_filtro = st.selectbox(
                    "Prioridade",
                    options=["Todos"] + PRIORIDADES,
                    key="hist_prio",
                )
            with f7:
                usar_datas = st.checkbox("Filtrar por intervalo de datas", value=False)
            with f8:
                busca_txt = st.text_input(
                    "Busca Textual (TAG, falha, diagnóstico ou causa raiz)",
                    placeholder="Ex: feeder, resistência, ICT, correia...",
                    key="hist_busca",
                )

            data_ini_str = None
            data_fim_str = None
            if usar_datas:
                d1, d2 = st.columns(2)
                with d1:
                    dt_ini = st.date_input("Data Inicial", value=datetime.now().date())
                    data_ini_str = dt_ini.strftime("%Y-%m-%d")
                with d2:
                    dt_fim = st.date_input("Data Final", value=datetime.now().date())
                    data_fim_str = dt_fim.strftime("%Y-%m-%d")

        registros = listar_historico_chamados(
            equipamento_id=eq_filtro[0],
            tecnico_id=tec_filtro[0],
            setor=setor_filtro,
            status_chamado=status_filtro,
            tipo_manutencao=tipo_filtro,
            prioridade=prio_filtro,
            data_inicio=data_ini_str,
            data_fim=data_fim_str,
            busca_texto=busca_txt,
        )

        if not registros:
            st.info("Nenhum registro de manutenção encontrado para os filtros aplicados.")
        else:
            df_hist = pd.DataFrame(registros)[
                [
                    "id",
                    "equipamento_tag",
                    "equipamento_nome",
                    "setor",
                    "posto_trabalho",
                    "prioridade",
                    "tipo_manutencao",
                    "status_chamado",
                    "operador_nome",
                    "tecnico_nome",
                    "data_hora_abertura",
                    "data_hora_inicio_atendimento",
                    "data_hora_fim_atendimento",
                    "downtime_minutos",
                    "descricao_falha",
                    "diagnostico_tecnico",
                    "causa_raiz",
                    "resumo_pecas",
                ]
            ].rename(
                columns={
                    "id": "Nº OS",
                    "equipamento_tag": "TAG",
                    "equipamento_nome": "Equipamento",
                    "setor": "Setor",
                    "posto_trabalho": "Posto",
                    "prioridade": "Prioridade",
                    "tipo_manutencao": "Tipo",
                    "status_chamado": "Status",
                    "operador_nome": "Solicitante",
                    "tecnico_nome": "Técnico",
                    "data_hora_abertura": "Abertura (UTC)",
                    "data_hora_inicio_atendimento": "Início Reparo (UTC)",
                    "data_hora_fim_atendimento": "Fim Reparo (UTC)",
                    "downtime_minutos": "Downtime (min)",
                    "descricao_falha": "Falha Observada",
                    "diagnostico_tecnico": "Diagnóstico Técnico",
                    "causa_raiz": "Causa Raiz",
                    "resumo_pecas": "Peças Substituídas",
                }
            )

            col_res, col_exp = st.columns([3, 1.2])
            with col_res:
                total_dt = sum(int(r["downtime_minutos"] or 0) for r in registros)
                st.markdown(
                    f"**Total de registros encontrados:** `{len(registros)}` &nbsp;|&nbsp; "
                    f"**Downtime soma na seleção:** `{total_dt} min`"
                )
            with col_exp:
                csv_bytes = df_hist.to_csv(index=False, sep=";").encode("utf-8-sig")
                st.download_button(
                    label="📥 Exportar Histórico para CSV",
                    data=csv_bytes,
                    file_name=f"historico_manutencao_amatech_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True,
                )

            st.dataframe(df_hist, use_container_width=True, hide_index=True, height=420)

    with aba_auditoria:
        st.markdown(
            "Registro cronológico e imutável de todas as alterações de status operacional das máquinas "
            "(`historico_status` — conformidade com **RN08** e **F17**)."
        )
        auditoria = listar_historico_auditoria(limite=200)
        if not auditoria:
            st.info("Nenhum evento de auditoria registrado.")
        else:
            df_aud = pd.DataFrame(auditoria)[
                [
                    "id",
                    "alterado_em",
                    "equipamento_tag",
                    "equipamento_nome",
                    "chamado_id",
                    "status_anterior",
                    "status_novo",
                    "usuario_nome",
                    "usuario_perfil",
                ]
            ].rename(
                columns={
                    "id": "ID Log",
                    "alterado_em": "Timestamp (UTC)",
                    "equipamento_tag": "TAG",
                    "equipamento_nome": "Equipamento",
                    "chamado_id": "Nº OS Vinculada",
                    "status_anterior": "Status Anterior",
                    "status_novo": "Novo Status",
                    "usuario_nome": "Responsável pela Ação",
                    "usuario_perfil": "Perfil",
                }
            )

            csv_aud = df_aud.to_csv(index=False, sep=";").encode("utf-8-sig")
            st.download_button(
                label="📥 Exportar Trilha de Auditoria (CSV)",
                data=csv_aud,
                file_name=f"auditoria_status_amatech_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )
            st.dataframe(df_aud, use_container_width=True, hide_index=True, height=400)


if __name__ == "__main__":
    render()
