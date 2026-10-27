"""
Tela 5: Ordem de Serviço em Atendimento (F07, F08, F09, RN03, RN04, RN05, RN08, RN09).
Exibe cronômetro de tempo de atendimento em execução, formulário de laudo técnico,
seleção de peças substituídas e botão de conclusão da OS com cálculo automático de downtime.
"""
import pandas as pd
import streamlit as st

from config import CAUSAS_RAIZ_PADRAO, COLORS, TIPOS_MANUTENCAO
from services.chamado_service import (
    adicionar_peca_chamado,
    calcular_segundos_decorridos,
    cancelar_chamado,
    concluir_chamado,
    listar_chamados_em_andamento,
    remover_peca_chamado,
    salvar_progresso_laudo,
)
from services.equipamento_service import listar_pecas
from ui_components import (
    badge_prioridade_html,
    formatar_relogio_hms,
    navegar_para,
    renderizar_cabecalho,
)


def _renderizar_cronometro_os(abertura_str: str | None, inicio_str: str | None) -> None:
    """Renderiza o cronômetro em tempo real do reparo e do downtime total."""
    seg_reparo = calcular_segundos_decorridos(inicio_str)
    seg_total = calcular_segundos_decorridos(abertura_str)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="timer-box">
                <div class="timer-label">⏱️ Cronômetro de Atendimento Técnico (Reparo)</div>
                <div class="timer-value">{formatar_relogio_hms(seg_reparo)}</div>
                <div style="font-size:0.78rem; color:#94A3B8; margin-top:4px;">
                    Início do Atendimento (UTC): {inicio_str or '-'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="timer-box" style="border-color: #D32F2F;">
                <div class="timer-label">🚨 Tempo Total de Máquina Parada (Downtime Corrido)</div>
                <div class="timer-value" style="color: #F87171;">{formatar_relogio_hms(seg_total)}</div>
                <div style="font-size:0.78rem; color:#94A3B8; margin-top:4px;">
                    Abertura do Chamado (UTC): {abertura_str or '-'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render() -> None:
    """Renderiza a Tela 5: Ordem de Serviço em Atendimento."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_cabecalho(
        "🔧 Ordem de Serviço em Atendimento",
        "Execução de reparo, apontamento de peças substituídas e emissão de laudo técnico",
        f"Executor: {usuario['nome']} ({usuario['perfil']})",
    )

    chamados_ativos = listar_chamados_em_andamento()

    if not chamados_ativos:
        st.info(
            "Não há nenhuma Ordem de Serviço com status **EM_ANDAMENTO** no momento. "
            "Acesse a **Fila Técnica** para assumir um chamado aberto."
        )
        if st.button("📋 Ir para a Fila de Chamados", type="primary"):
            navegar_para("fila_chamados")
        return

    opcoes_ids = [c["id"] for c in chamados_ativos]
    mapa_os = {c["id"]: c for c in chamados_ativos}

    os_pre = st.session_state.get("os_selecionada_id")
    idx_os = opcoes_ids.index(os_pre) if os_pre in opcoes_ids else 0

    col_sel, col_ref = st.columns([3.5, 1])
    with col_sel:
        os_id_sel = st.selectbox(
            "Selecione a Ordem de Serviço em Atendimento",
            options=opcoes_ids,
            index=idx_os,
            format_func=lambda cid: (
                f"OS #{cid} — {mapa_os[cid]['equipamento_tag']} ({mapa_os[cid]['equipamento_nome']}) "
                f"| Técnico: {mapa_os[cid]['tecnico_nome'] or 'Não atribuído'} "
                f"| Prioridade: {mapa_os[cid]['prioridade']}"
            ),
            key="select_os_atendimento",
        )
    with col_ref:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar Relógio", use_container_width=True):
            st.rerun()

    os_atual = mapa_os[os_id_sel]

    # Cronômetro com atualização automática a cada 2 segundos via fragment (se disponível)
    if hasattr(st, "fragment"):
        @st.fragment(run_every="2s")
        def _bloco_cronometro() -> None:
            _renderizar_cronometro_os(
                os_atual.get("data_hora_abertura"),
                os_atual.get("data_hora_inicio_atendimento"),
            )

        _bloco_cronometro()
    else:
        _renderizar_cronometro_os(
            os_atual.get("data_hora_abertura"),
            os_atual.get("data_hora_inicio_atendimento"),
        )

    # Cabeçalho de Detalhes da OS
    st.markdown(
        f"""
        <div style="background:#FFFFFF; padding:16px 20px; border-radius:10px; margin-bottom:18px;
                    border-left:5px solid {COLORS['EM_MANUTENCAO']}; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
                <span style="font-size:1.15rem; font-weight:800; color:{COLORS['primary']};">
                    OS #{os_atual['id']} • Máquina: {os_atual['equipamento_tag']} — {os_atual['equipamento_nome']}
                </span>
                <span>{badge_prioridade_html(os_atual['prioridade'])}</span>
            </div>
            <div style="font-size:0.9rem; color:#334155; margin-top:8px;">
                <strong>Falha Reportada pelo Operador ({os_atual['operador_nome']}):</strong>
                {os_atual['descricao_falha']}
            </div>
            <div style="font-size:0.82rem; color:#64748B; margin-top:6px;">
                📍 Setor: <strong>{os_atual['setor']}</strong> ({os_atual['posto_trabalho'] or 'Posto 01'})
                &nbsp;|&nbsp; 👷 Técnico Responsável: <strong>{os_atual['tecnico_nome']}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_laudo, col_pecas = st.columns([1.35, 1])

    # Coluna Direita: Gestão de Peças Substituídas (F08 / RN09)
    with col_pecas:
        st.subheader("🔩 Peças e Insumos Substituídos (F08)")
        catalogo_pecas = listar_pecas(apenas_ativas=True)

        if not catalogo_pecas:
            st.warning("Nenhuma peça ativa no catálogo.")
        else:
            mapa_pecas = {p["id"]: p for p in catalogo_pecas}
            with st.form(f"form_add_peca_{os_atual['id']}", clear_on_submit=True):
                peca_id_sel = st.selectbox(
                    "Selecionar Peça do Catálogo",
                    options=[p["id"] for p in catalogo_pecas],
                    format_func=lambda pid: (
                        f"{mapa_pecas[pid]['codigo_peca']} — {mapa_pecas[pid]['nome']} "
                        f"({mapa_pecas[pid]['unidade_medida']})"
                    ),
                )
                qtd_peca = st.number_input(
                    "Quantidade Substituída (RN09: > 0)",
                    min_value=0.1,
                    value=1.0,
                    step=1.0,
                    format="%.2f",
                )
                btn_add_peca = st.form_submit_button(
                    "➕ Incluir Peça na OS",
                    use_container_width=True,
                )
                if btn_add_peca:
                    try:
                        adicionar_peca_chamado(
                            chamado_id=os_atual["id"],
                            peca_id=peca_id_sel,
                            quantidade=qtd_peca,
                        )
                        st.success("Peça vinculada à Ordem de Serviço!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao incluir peça: {exc}")

        st.markdown("##### Peças vinculadas a esta OS:")
        pecas_os = os_atual.get("pecas_trocadas", [])
        if not pecas_os:
            st.caption("Nenhuma peça substituída registrada nesta OS até o momento.")
        else:
            for item_p in pecas_os:
                cp1, cp2 = st.columns([4, 1])
                with cp1:
                    st.markdown(
                        f"**{item_p['codigo_peca']}** — {item_p['nome']} "
                        f"(`{item_p['quantidade']:g} {item_p['unidade']}`)"
                    )
                with cp2:
                    if st.button("🗑️", key=f"del_peca_{item_p['id']}", help="Remover peça"):
                        remover_peca_chamado(item_p["id"])
                        st.rerun()

    # Coluna Esquerda: Formulário de Laudo Técnico e Conclusão (F07, F09, RN04, RN05)
    with col_laudo:
        st.subheader("📝 Laudo Técnico de Manutenção (F07 / F09)")

        causa_atual = os_atual.get("causa_raiz") or ""
        opcoes_causa = list(CAUSAS_RAIZ_PADRAO)
        if causa_atual and causa_atual not in opcoes_causa:
            opcoes_causa.insert(0, causa_atual)

        idx_causa = opcoes_causa.index(causa_atual) if causa_atual in opcoes_causa else 0
        idx_tipo = (
            TIPOS_MANUTENCAO.index(os_atual["tipo_manutencao"])
            if os_atual.get("tipo_manutencao") in TIPOS_MANUTENCAO
            else 0
        )

        with st.form(f"form_concluir_os_{os_atual['id']}", clear_on_submit=False):
            tipo_manut = st.selectbox(
                "Tipo de Manutenção Executada *",
                options=TIPOS_MANUTENCAO,
                index=idx_tipo,
            )

            causa_sel = st.selectbox(
                "Causa Raiz Identificada (Padronizada) *",
                options=opcoes_causa,
                index=idx_causa,
            )

            causa_custom = st.text_input(
                "Especificar Causa Raiz (opcional — preencha se desejar detalhar)",
                value="",
                placeholder="Deixe em branco para usar a causa selecionada acima",
            )

            diagnostico = st.text_area(
                "Diagnóstico Técnico e Serviço Realizado * (Obrigatório RN04)",
                value=os_atual.get("diagnostico_tecnico") or "",
                height=135,
                placeholder=(
                    "Descreva tecnicamente a causa encontrada, os testes efetuados e o reparo "
                    "realizado para liberar o equipamento..."
                ),
            )

            st.info(
                "📌 **Regra RN05:** Ao concluir a OS, o sistema gravará `data_hora_fim_atendimento = now()`, "
                "calculará automaticamente o `downtime_minutos` e retornará a máquina para **OPERACIONAL (Verde)**."
            )

            cb1, cb2 = st.columns(2)
            with cb1:
                btn_concluir = st.form_submit_button(
                    "✅ Concluir OS e Liberar Máquina",
                    type="primary",
                    use_container_width=True,
                )
            with cb2:
                btn_rascunho = st.form_submit_button(
                    "💾 Salvar Progresso do Laudo",
                    use_container_width=True,
                )

            causa_final = causa_custom.strip() if causa_custom.strip() else causa_sel

            if btn_rascunho:
                try:
                    salvar_progresso_laudo(
                        chamado_id=os_atual["id"],
                        diagnostico_tecnico=diagnostico,
                        causa_raiz=causa_final,
                        tipo_manutencao=tipo_manut,
                    )
                    st.success("💾 Rascunho do laudo técnico salvo com sucesso!")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao salvar progresso: {exc}")

            if btn_concluir:
                try:
                    res = concluir_chamado(
                        chamado_id=os_atual["id"],
                        usuario_id=usuario["id"],
                        diagnostico_tecnico=diagnostico,
                        causa_raiz=causa_final,
                        tipo_manutencao=tipo_manut,
                    )
                    st.success(
                        f"🎉 **OS #{res['chamado_id']} concluída com sucesso!** "
                        f"Downtime calculado: **{res['downtime_minutos']} minutos**. "
                        f"A máquina **{os_atual['equipamento_tag']}** voltou para **OPERACIONAL**."
                    )
                    navegar_para("painel_maquinas")
                except Exception as exc:
                    st.error(f"❌ Erro ao concluir OS: {exc}")

        # Opção de cancelamento de chamado por alarme falso (Supervisor/Gestor ou Técnico)
        with st.expander("⚠️ Cancelar Ordem de Serviço (Alarme Falso / Chamado Indevido)"):
            motivo_canc = st.text_input(
                "Motivo do Cancelamento",
                value="Alarme falso / Reset operacional sem necessidade de intervenção",
                key=f"motivo_canc_{os_atual['id']}",
            )
            if st.button(
                "🚫 Confirmar Cancelamento da OS",
                key=f"btn_canc_{os_atual['id']}",
            ):
                try:
                    cancelar_chamado(
                        chamado_id=os_atual["id"],
                        usuario_id=usuario["id"],
                        motivo_cancelamento=motivo_canc,
                    )
                    st.warning(f"OS #{os_atual['id']} cancelada e máquina liberada.")
                    navegar_para("painel_maquinas")
                except Exception as exc:
                    st.error(f"Erro ao cancelar OS: {exc}")


if __name__ == "__main__":
    render()
