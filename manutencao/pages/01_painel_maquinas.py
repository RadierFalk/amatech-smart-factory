"""
Tela de Painel de Máquinas (F02, RNF04).
Replica o design, KPIs, barra de filtros com legenda, agrupamento por Estação (Etapa)
e cards de máquinas com modal rápido de abertura de chamado do projeto amatech-manutencao.
"""
from datetime import datetime
import streamlit as st

from config import ESTACOES_FLUXO, PRIORIDADES
from services.chamado_service import abrir_chamado
from services.equipamento_service import listar_equipamentos, listar_setores
from services.relatorio_service import obter_indicadores_consolidados
from ui_components import (
    esc,
    formatar_duracao_curta,
    formatar_duracao_hm,
    kpi_html,
    navegar_para,
    renderizar_topbar,
    rotulo_amigavel,
    selo_html,
)


def _abrir_modal_chamado_rapido(maquina: dict, usuario: dict) -> None:
    """Abre um modal (st.dialog) idêntico ao A.abrirModalChamado do projeto de referência."""
    if hasattr(st, "dialog"):
        @st.dialog(f"Abrir chamado de manutenção — {maquina['codigo_tag']}", width="large")
        def _modal() -> None:
            _conteudo_modal_chamado(maquina, usuario)

        _modal()
    else:
        navegar_para("abrir_chamado", equipamento_preselecionado_id=maquina["id"])


def _conteudo_modal_chamado(maquina: dict, usuario: dict) -> None:
    st.markdown(
        """
        <div class="aviso-info">
          <span>⏱</span>
          <div><strong>Timestamp automático.</strong> Ao confirmar, o sistema grava a data/hora da abertura
          e marca a máquina como <strong>INDISPONÍVEL</strong>, iniciando o cronômetro de downtime.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.text_input("Máquina", value=f"{maquina['codigo_tag']} — {maquina['nome']}", disabled=True)
    with c2:
        st.text_input("Estação / setor", value=maquina["setor"], disabled=True)
    with c3:
        st.text_input("Posto de trabalho", value=maquina.get("posto_trabalho") or "Posto 01", disabled=True)

    prioridade = st.segmented_control(
        "Prioridade *",
        options=PRIORIDADES,
        default="MEDIA",
        format_func=rotulo_amigavel,
    ) if hasattr(st, "segmented_control") else st.radio(
        "Prioridade *",
        options=PRIORIDADES,
        index=1,
        horizontal=True,
        format_func=rotulo_amigavel,
    )
    st.caption("Use **Crítica** quando a parada interrompe toda a linha.")

    descricao = st.text_area(
        "Descrição da falha *",
        placeholder="Ex.: insersora parou no meio do ciclo e apresenta erro de posicionamento do nozzle.",
    )
    st.caption("Descreva o que foi observado. O técnico complementará com o diagnóstico.")

    cb1, cb2 = st.columns([1, 1])
    with cb1:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()
    with cb2:
        if st.button("Confirmar abertura", type="primary", use_container_width=True):
            try:
                novo_id = abrir_chamado(
                    equipamento_id=maquina["id"],
                    operador_abertura_id=usuario["id"],
                    prioridade=prioridade or "MEDIA",
                    descricao_falha=descricao,
                    tipo_manutencao="CORRETIVA",
                )
                st.toast(f"Chamado #{novo_id} registrado com sucesso!", icon="✅")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _renderizar_conteudo_painel(
    busca: str,
    setor_sel: str,
    estado_sel: str,
    usuario: dict,
) -> None:
    todos_eq = listar_equipamentos(apenas_ativos=True)
    ind_geral = obter_indicadores_consolidados(periodo_dias=30)

    total_maquinas = len(todos_eq)
    funcionando = sum(1 for m in todos_eq if m["status_operacional"] == "OPERACIONAL")
    em_manutencao = sum(1 for m in todos_eq if m["status_operacional"] == "EM_MANUTENCAO")
    indisponivel = sum(1 for m in todos_eq if m["status_operacional"] == "PARADA")
    total_paradas = indisponivel + em_manutencao
    disp_pct = round((funcionando / total_maquinas) * 100, 1) if total_maquinas else 100.0
    downtime_min = int(ind_geral["downtime_total_minutos"] or 0)
    downtime_horas = round(downtime_min / 60.0, 1)

    # 4 KPIs Superiores idênticos ao telas-operador.js
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            kpi_html(
                "Máquinas funcionando",
                str(funcionando),
                unidade=f"/ {total_maquinas}",
                detalhe=f"Disponibilidade: {disp_pct}%",
                variante="verde",
            ),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_html(
                "Em manutenção",
                str(em_manutencao),
                detalhe="Atendimento técnico em andamento",
                variante="amarelo",
            ),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_html(
                "Indisponíveis",
                str(indisponivel),
                detalhe="Aguardando atendimento",
                variante="vermelho",
            ),
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            kpi_html(
                "Downtime acumulado",
                formatar_duracao_hm(downtime_min),
                unidade="",
                detalhe=f"{downtime_min} min ({downtime_horas:g} h) · MTTR de {ind_geral['mttr_minutos']:g} min",
                variante="azul",
            ),
            unsafe_allow_html=True,
        )

    # Legenda + horário de atualização
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin: 4px 0 12px 0; flex-wrap:wrap; gap:10px;">
          <div class="legenda">
            <span><i class="dot-funcionando"></i>Funcionando</span>
            <span><i class="dot-em_manutencao"></i>Em manutenção</span>
            <span><i class="dot-indisponivel"></i>Indisponível</span>
          </div>
          <span style="font-size:11.5px; color:var(--cinza-500);">
            Atualizado às {datetime.now().strftime('%H:%M:%S')} · atualização automática a cada 8s
          </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Aplicação dos filtros
    termo = (busca or "").strip().lower()
    filtradas = []
    for m in todos_eq:
        if termo and termo not in f"{m['codigo_tag']} {m['nome']}".lower():
            continue
        if setor_sel and setor_sel != "Todas as estações" and m["setor"] != setor_sel:
            continue
        if estado_sel and estado_sel != "Todos os estados" and m["status_operacional"] != estado_sel:
            continue
        filtradas.append(m)

    if not filtradas:
        st.markdown(
            '<div class="card"><div class="vazio"><strong>Nenhuma máquina encontrada</strong>Ajuste os filtros de busca.</div></div>',
            unsafe_allow_html=True,
        )
        return

    # Agrupamento por Estação (Etapa do Processo Produtivo)
    por_setor: dict[str, list[dict]] = {}
    for m in filtradas:
        por_setor.setdefault(m["setor"], []).append(m)

    setores_ordenados = sorted(
        por_setor.keys(),
        key=lambda s: ESTACOES_FLUXO.get(s, (99, s, ""))[0],
    )

    for idx_est, nome_setor in enumerate(setores_ordenados, start=1):
        maquinas_estacao = sorted(por_setor[nome_setor], key=lambda x: x["codigo_tag"])
        ordem_etapa = ESTACOES_FLUXO.get(nome_setor, (idx_est, nome_setor[:3].upper(), ""))[0]
        paradas_est = sum(1 for m in maquinas_estacao if m["status_operacional"] != "OPERACIONAL")
        alerta_html = (
            f'<span class="alerta-estacao">{paradas_est} fora de operação</span>'
            if paradas_est > 0
            else ""
        )

        st.markdown(
            f"""
            <div class="grupo-estacao-cabecalho">
              <span class="etapa">ETAPA {ordem_etapa}</span>
              <h3>{esc(nome_setor)}</h3>
              <span class="contagem">{len(maquinas_estacao)} máquina(s)</span>
              {alerta_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        colunas_por_linha = 4
        for i in range(0, len(maquinas_estacao), colunas_por_linha):
            cols = st.columns(colunas_por_linha)
            for j, m in enumerate(maquinas_estacao[i : i + colunas_por_linha]):
                with cols[j]:
                    estado = m["status_operacional"]
                    os_id = m.get("os_ativa_id")
                    prio = m.get("os_ativa_prioridade")
                    tempo_min = m.get("tempo_decorrido_min") or 0

                    if os_id:
                        os_html = (
                            f'<div class="os-link">OS <strong>#{os_id}</strong> · {esc(rotulo_amigavel(prio))} '
                            f'· parada há <strong>{formatar_duracao_curta(tempo_min)}</strong></div>'
                        )
                    else:
                        os_html = '<div class="os-link" style="color:var(--verde);font-weight:600;">Sem chamado ativo</div>'

                    st.markdown(
                        f"""
                        <article class="maquina-card" data-estado="{esc(estado)}">
                          <div style="display:flex;align-items:center;gap:8px">
                            <span class="tag">{esc(m['codigo_tag'])}</span>
                            <span style="margin-left:auto">{selo_html(estado)}</span>
                          </div>
                          <div class="nome">{esc(m['nome'])}</div>
                          <div class="meta">{esc(m.get('posto_trabalho') or 'Posto 01')}</div>
                          {os_html}
                        </article>
                        """,
                        unsafe_allow_html=True,
                    )

                    if os_id:
                        if st.button(
                            f"Ver OS #{os_id}",
                            key=f"btn_ver_os_{m['id']}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            navegar_para("ordem_servico", os_selecionada_id=os_id)
                    else:
                        if st.button(
                            "Abrir chamado",
                            key=f"btn_abrir_maq_{m['id']}",
                            type="primary",
                            use_container_width=True,
                        ):
                            _abrir_modal_chamado_rapido(m, usuario)


def render() -> None:
    """Renderiza o Painel de Máquinas."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar o painel.")
        return

    renderizar_topbar(
        "Painel de máquinas",
        "Situação das máquinas por estação do processo produtivo",
    )

    # Barra de filtros idêntica ao .filtros-barra
    f1, f2, f3, f4 = st.columns([1.6, 1.4, 1.2, 0.7])
    with f1:
        busca = st.text_input(
            "Buscar",
            placeholder="Buscar máquina ou TAG…",
            label_visibility="collapsed",
            key="painel_busca",
        )
    with f2:
        setores_opcoes = ["Todas as estações"] + listar_setores()
        setor_sel = st.selectbox(
            "Estação",
            options=setores_opcoes,
            label_visibility="collapsed",
            key="painel_estacao",
        )
    with f3:
        opcoes_estado = [
            ("Todos os estados", "Todos os estados"),
            ("OPERACIONAL", "Funcionando"),
            ("EM_MANUTENCAO", "Em manutenção"),
            ("PARADA", "Indisponível"),
        ]
        estado_sel = st.selectbox(
            "Estado",
            options=[x[0] for x in opcoes_estado],
            format_func=lambda k: dict(opcoes_estado)[k],
            label_visibility="collapsed",
            key="painel_estado",
        )
    with f4:
        if st.button("↻ Atualizar", type="secondary", use_container_width=True):
            st.rerun()

    if hasattr(st, "fragment"):
        @st.fragment(run_every="8s")
        def _painel_vivo() -> None:
            _renderizar_conteudo_painel(busca, setor_sel, estado_sel, usuario)

        _painel_vivo()
    else:
        _renderizar_conteudo_painel(busca, setor_sel, estado_sel, usuario)


if __name__ == "__main__":
    render()
