"""
Tela 2: Painel Sinótico de Máquinas (F02, RF06).
Exibe cards em grid com status visual colorido (Verde/Amarelo/Vermelho),
indicadores rápidos, filtro por setor, auto-refresh a cada 5-10s e botão 'Abrir Chamado'.
"""
from datetime import datetime
import streamlit as st

from config import COLORS
from services.equipamento_service import listar_equipamentos, listar_setores
from ui_components import (
    badge_prioridade_html,
    badge_status_equipamento_html,
    formatar_duracao_hm,
    navegar_para,
    renderizar_cabecalho,
    renderizar_kpi_card,
)


def _renderizar_grid_maquinas(setor_selecionado: str, usuario: dict) -> None:
    """Renderiza os indicadores de topo e o grid de cards de equipamentos."""
    equipamentos = listar_equipamentos(setor=setor_selecionado, apenas_ativos=True)

    total = len(equipamentos)
    operacionais = sum(1 for e in equipamentos if e["status_operacional"] == "OPERACIONAL")
    em_manutencao = sum(1 for e in equipamentos if e["status_operacional"] == "EM_MANUTENCAO")
    paradas = sum(1 for e in equipamentos if e["status_operacional"] == "PARADA")

    # Indicadores Rápidos no Topo
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        renderizar_kpi_card(
            "Total de Máquinas",
            str(total),
            f"Setor: {setor_selecionado}",
            COLORS["primary"],
        )
    with c2:
        renderizar_kpi_card(
            "Operacionais (Verde)",
            str(operacionais),
            "Produzindo normalmente",
            COLORS["OPERACIONAL"],
        )
    with c3:
        renderizar_kpi_card(
            "Em Manutenção (Amarelo)",
            str(em_manutencao),
            "Técnico em atendimento",
            COLORS["EM_MANUTENCAO"],
        )
    with c4:
        renderizar_kpi_card(
            "Máquinas Paradas (Vermelho)",
            str(paradas),
            "Aguardando atendimento",
            COLORS["PARADA"],
        )

    st.caption(
        f"🔄 Última sincronização com o chão de fábrica: **{datetime.now().strftime('%H:%M:%S')}**"
    )

    if not equipamentos:
        st.info("Nenhum equipamento ativo encontrado para o setor selecionado.")
        return

    # Grid Responsivo de Cards (3 colunas por linha para ótima leitura em tablets e desktops)
    colunas_por_linha = 3
    for i in range(0, len(equipamentos), colunas_por_linha):
        cols = st.columns(colunas_por_linha)
        for idx, eq in enumerate(equipamentos[i : i + colunas_por_linha]):
            with cols[idx]:
                status = eq["status_operacional"]
                cor_topo = COLORS.get(status, COLORS["primary"])
                badge_html = badge_status_equipamento_html(status)

                os_id = eq.get("os_ativa_id")
                tempo_min = eq.get("tempo_decorrido_min")
                prioridade = eq.get("os_ativa_prioridade")
                tecnico = eq.get("os_ativa_tecnico")
                descricao = eq.get("os_ativa_descricao") or ""

                if status == "OPERACIONAL":
                    detalhe_os_html = (
                        '<div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; '
                        'padding:10px; font-size:0.83rem; color:#065F46; min-height:74px;">'
                        "✅ <strong>Linha liberada.</strong><br>Nenhuma Ordem de Serviço pendente."
                        "</div>"
                    )
                elif status == "PARADA":
                    prio_badge = badge_prioridade_html(prioridade) if prioridade else ""
                    detalhe_os_html = (
                        f'<div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:8px; '
                        f'padding:10px; font-size:0.83rem; color:#991B1B; min-height:74px;">'
                        f'🚨 <strong>OS #{os_id} Aberta</strong> {prio_badge}<br>'
                        f'⏱️ Parada há: <strong>{formatar_duracao_hm(tempo_min)}</strong><br>'
                        f'<span style="color:#7F1D1D;">{descricao[:65]}{"..." if len(descricao) > 65 else ""}</span>'
                        f"</div>"
                    )
                else:  # EM_MANUTENCAO
                    prio_badge = badge_prioridade_html(prioridade) if prioridade else ""
                    nome_tec = tecnico or "Técnico designado"
                    detalhe_os_html = (
                        f'<div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; '
                        f'padding:10px; font-size:0.83rem; color:#92400E; min-height:74px;">'
                        f'🔧 <strong>OS #{os_id} em Reparo</strong> {prio_badge}<br>'
                        f'👷 Técnico: <strong>{nome_tec}</strong> | ⏱️ <strong>{formatar_duracao_hm(tempo_min)}</strong><br>'
                        f'<span style="color:#78350F;">{descricao[:60]}{"..." if len(descricao) > 60 else ""}</span>'
                        f"</div>"
                    )

                st.markdown(
                    f"""
                    <div class="machine-card" style="border-top-color: {cor_topo};">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="machine-tag">{eq['codigo_tag']}</span>
                            <span style="font-size:0.78rem; background:#F1F5F9; padding:3px 8px; border-radius:6px; font-weight:600; color:#475569;">
                                {eq['setor']} • {eq['posto_trabalho'] or 'Posto'}
                            </span>
                        </div>
                        <div class="machine-name">{eq['nome']}</div>
                        {badge_html}
                        {detalhe_os_html}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                perfil = usuario.get("perfil", "OPERADOR")

                # Botão de Ação Rápida respeitando RN02 (Bloqueio de Redundância) e RBAC
                if status == "OPERACIONAL":
                    if perfil in ("OPERADOR", "GESTOR"):
                        if st.button(
                            f"🚨 Abrir Chamado ({eq['codigo_tag']})",
                            key=f"btn_abrir_{eq['id']}",
                            use_container_width=True,
                            type="primary",
                        ):
                            navegar_para("abrir_chamado", equipamento_preselecionado_id=eq["id"])
                    else:
                        st.button(
                            "✅ Máquina em Operação",
                            key=f"btn_ok_{eq['id']}",
                            disabled=True,
                            use_container_width=True,
                        )
                else:
                    # Máquina já PARADA ou EM_MANUTENCAO -> RN02 bloqueia novo chamado
                    if perfil in ("TECNICO", "GESTOR") and os_id:
                        if status == "PARADA":
                            if st.button(
                                f"🛠️ Ir para Fila (OS #{os_id})",
                                key=f"btn_fila_{eq['id']}",
                                use_container_width=True,
                            ):
                                navegar_para("fila_chamados", os_destaque_id=os_id)
                        else:
                            if st.button(
                                f"🔧 Gerenciar OS #{os_id}",
                                key=f"btn_os_{eq['id']}",
                                use_container_width=True,
                            ):
                                navegar_para("ordem_servico", os_selecionada_id=os_id)
                    else:
                        st.button(
                            f"🔒 Bloqueado RN02 (OS #{os_id} Ativa)",
                            key=f"btn_bloq_{eq['id']}",
                            disabled=True,
                            use_container_width=True,
                        )


def render() -> None:
    """Renderiza a Tela 2: Painel Sinótico de Máquinas."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar o painel.")
        return

    renderizar_cabecalho(
        "🏭 Painel Sinótico de Máquinas — Chão de Fábrica",
        "Monitoramento em tempo real das linhas SMT, Testes Funcionais, Montagem e Embalagem",
        f"Perfil: {usuario['perfil']}",
    )

    # Barra de Filtros e Controle de Auto-Refresh (5 a 10s conforme RF06 / F02)
    col_f1, col_f2, col_f3 = st.columns([2, 1.5, 1])
    setores_disponiveis = ["Todos"] + listar_setores()

    with col_f1:
        setor_sel = st.selectbox(
            "Filtrar por Setor Produtivo",
            options=setores_disponiveis,
            index=0,
            key="filtro_setor_painel",
        )
    with col_f2:
        intervalo_refresh = st.selectbox(
            "Auto-Refresh do Painel Sinótico",
            options=[
                ("Ativo (a cada 5 segundos)", 5),
                ("Ativo (a cada 10 segundos)", 10),
                ("Pausado (atualização manual)", 0),
            ],
            format_func=lambda x: x[0],
            index=1,
            key="auto_refresh_painel_cfg",
        )
    with col_f3:
        st.write("")
        st.write("")
        if st.button("🔄 Atualizar Agora", use_container_width=True):
            st.rerun()

    segundos_refresh = intervalo_refresh[1]

    # Se o Streamlit suportar st.fragment com run_every, atualiza o grid automaticamente sem piscar a tela
    if segundos_refresh > 0 and hasattr(st, "fragment"):
        @st.fragment(run_every=f"{segundos_refresh}s")
        def _painel_auto_refresh() -> None:
            _renderizar_grid_maquinas(setor_sel, usuario)

        _painel_auto_refresh()
    else:
        _renderizar_grid_maquinas(setor_sel, usuario)


if __name__ == "__main__":
    render()
