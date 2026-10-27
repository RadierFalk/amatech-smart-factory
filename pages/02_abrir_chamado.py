"""
Tela 3: Abertura Rápida de Chamado (F03, F04, RN02, RN06, RN08).
Permite ao Operador ou Gestor abrir uma Ordem de Serviço selecionando o equipamento,
prioridade (Baixa, Média, Alta, Crítica), tipo de manutenção e descrição da falha.
"""
import pandas as pd
import streamlit as st

from config import COLORS, PRIORIDADES, TIPOS_MANUTENCAO
from services.chamado_service import abrir_chamado, listar_historico_chamados
from services.equipamento_service import listar_equipamentos
from ui_components import (
    badge_prioridade_html,
    badge_status_equipamento_html,
    navegar_para,
    renderizar_cabecalho,
)


def render() -> None:
    """Renderiza a Tela 3: Abertura Rápida de Chamado e Acompanhamento do Operador."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_cabecalho(
        "🚨 Abertura Rápida de Chamado de Manutenção",
        "Acionamento imediato da equipe técnica com registro formal de parada de linha",
        f"Solicitante: {usuario['nome']} ({usuario['matricula']})",
    )

    equipamentos = listar_equipamentos(apenas_ativos=True)
    if not equipamentos:
        st.error("Não há equipamentos ativos cadastrados no sistema.")
        return

    # Ordena por código TAG para facilitar localização rápida pelo operador
    equipamentos_ordenados = sorted(equipamentos, key=lambda x: x["codigo_tag"])
    opcoes_ids = [eq["id"] for eq in equipamentos_ordenados]
    mapa_eq = {eq["id"]: eq for eq in equipamentos_ordenados}

    preselecionado_id = st.session_state.get("equipamento_preselecionado_id")
    idx_inicial = opcoes_ids.index(preselecionado_id) if preselecionado_id in opcoes_ids else 0

    col_esq, col_dir = st.columns([1.35, 1])

    with col_esq:
        st.subheader("1. Identificação da Máquina e Falha")

        equip_id_sel = st.selectbox(
            "Selecione o Equipamento / Máquina *",
            options=opcoes_ids,
            index=idx_inicial,
            format_func=lambda eid: (
                f"{mapa_eq[eid]['codigo_tag']} — {mapa_eq[eid]['nome']} "
                f"[{mapa_eq[eid]['status_operacional']}]"
            ),
            key="select_equip_abertura",
        )

        eq_atual = mapa_eq[equip_id_sel]

        # Autopreenchimento bloqueado de Setor e Posto (F03)
        c_setor, c_posto = st.columns(2)
        with c_setor:
            st.text_input("Setor Produtivo (Automático)", value=eq_atual["setor"], disabled=True)
        with c_posto:
            st.text_input(
                "Posto de Trabalho (Automático)",
                value=eq_atual["posto_trabalho"] or "Posto 01",
                disabled=True,
            )

        maquina_bloqueada = eq_atual["status_operacional"] in ("PARADA", "EM_MANUTENCAO") or (
            eq_atual.get("os_ativa_id") is not None
        )

        if maquina_bloqueada:
            os_ativa_id = eq_atual.get("os_ativa_id")
            st.error(
                f"⛔ **Bloqueio de Redundância (RN02):** A máquina **{eq_atual['codigo_tag']}** já se encontra "
                f"com status **{eq_atual['status_operacional']}** vinculada à **OS #{os_ativa_id}**.\n\n"
                f"**Falha registrada na OS #{os_ativa_id}:** {eq_atual.get('os_ativa_descricao') or 'Em atendimento'}"
            )

        with st.form("form_abrir_chamado", clear_on_submit=False):
            c_prio, c_tipo = st.columns(2)
            with c_prio:
                prioridade_sel = st.radio(
                    "Nível de Prioridade *",
                    options=PRIORIDADES,
                    index=2,  # ALTA por padrão em paradas de linha
                    horizontal=True,
                )
            with c_tipo:
                tipo_sel = st.selectbox(
                    "Tipo de Manutenção *",
                    options=TIPOS_MANUTENCAO,
                    index=0,
                )

            descricao_falha = st.text_area(
                "Descrição do Sintoma / Falha Observada *",
                placeholder=(
                    "Descreva o problema apresentado pela máquina (ex: Alarme de pressão pneumática, "
                    "travamento de eixo, erro de comunicação no sensor óptico...)"
                ),
                height=120,
            )

            st.warning(
                "⚠️ **Atenção:** Ao confirmar a abertura, o carimbo de data/hora (`data_hora_abertura`) será "
                "gravado automaticamente no servidor e a máquina passará imediatamente para o status "
                "**PARADA (Vermelho)** no painel sinótico."
            )

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submeter = st.form_submit_button(
                    "🚨 Confirmar Abertura de OS",
                    use_container_width=True,
                    type="primary",
                    disabled=maquina_bloqueada,
                )
            with col_btn2:
                cancelar = st.form_submit_button(
                    "⬅️ Voltar ao Painel de Máquinas",
                    use_container_width=True,
                )

            if cancelar:
                navegar_para("painel_maquinas")

            if submeter:
                try:
                    novo_id = abrir_chamado(
                        equipamento_id=equip_id_sel,
                        operador_abertura_id=usuario["id"],
                        prioridade=prioridade_sel,
                        descricao_falha=descricao_falha,
                        tipo_manutencao=tipo_sel,
                    )
                    st.session_state["ultimo_chamado_criado"] = novo_id
                    st.success(
                        f"✅ **Ordem de Serviço #{novo_id}** aberta com sucesso! "
                        f"A máquina **{eq_atual['codigo_tag']}** foi marcada como **PARADA** e enviada à fila técnica."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Não foi possível abrir o chamado: {exc}")

    with col_dir:
        st.subheader("2. Status do Equipamento Selecionado")
        st.markdown(
            f"""
            <div style="background:#FFFFFF; padding:20px; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <div style="font-size:1.3rem; font-weight:800; color:{COLORS['primary']};">
                    {eq_atual['codigo_tag']} — {eq_atual['nome']}
                </div>
                <div style="font-size:0.9rem; color:#64748B; margin:6px 0 14px 0;">
                    Setor: <strong>{eq_atual['setor']}</strong> | Posto: <strong>{eq_atual['posto_trabalho'] or 'Posto 01'}</strong>
                </div>
                {badge_status_equipamento_html(eq_atual['status_operacional'])}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### Guia de Classificação de Prioridade")
        st.markdown(
            f"""
            <div style="background:#FFFFFF; padding:16px; border-radius:10px; font-size:0.86rem; line-height:1.7;">
                <div>{badge_prioridade_html('CRITICA')} — Parada total de linha gargalo (Forno SMT / ICT) ou risco de segurança.</div>
                <div style="margin-top:6px;">{badge_prioridade_html('ALTA')} — Máquina parada impactando meta horária do turno.</div>
                <div style="margin-top:6px;">{badge_prioridade_html('MEDIA')} — Falha parcial ou intermitente com operação degradada.</div>
                <div style="margin-top:6px;">{badge_prioridade_html('BAIXA')} — Ajuste leve, inspeção ou manutenção preventiva programada.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # F04: Acompanhamento dos Chamados Abertos pelo Operador / Recentes
    st.subheader("📋 Acompanhamento de Chamados Recentes (F04)")
    meus_chamados = listar_historico_chamados(
        operador_id=usuario["id"] if usuario["perfil"] == "OPERADOR" else None
    )
    if not meus_chamados:
        st.info("Nenhum chamado aberto por este usuário até o momento.")
    else:
        df_meus = pd.DataFrame(meus_chamados[:15])[
            [
                "id",
                "equipamento_tag",
                "equipamento_nome",
                "setor",
                "prioridade",
                "status_chamado",
                "data_hora_abertura",
                "tecnico_nome",
                "downtime_minutos",
                "descricao_falha",
            ]
        ].rename(
            columns={
                "id": "Nº OS",
                "equipamento_tag": "TAG",
                "equipamento_nome": "Equipamento",
                "setor": "Setor",
                "prioridade": "Prioridade",
                "status_chamado": "Status",
                "data_hora_abertura": "Abertura (UTC)",
                "tecnico_nome": "Técnico Responsável",
                "downtime_minutos": "Downtime (min)",
                "descricao_falha": "Descrição da Falha",
            }
        )
        st.dataframe(df_meus, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    render()
