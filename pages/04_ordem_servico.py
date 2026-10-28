"""
Tela de Ordem de Serviço (F07, F08, F09, RN03, RN04, RN05, RN08, RN09).
Replica fielmente o layout .os-topo (.os-cronometro + card Dados da OS),
cards Relato do operador / Diagnóstico técnico, Peças substituídas e Ações da OS
do projeto amatech-manutencao.
"""
from datetime import datetime, timezone
import streamlit as st

from config import CAUSAS_RAIZ_PADRAO, TIPOS_MANUTENCAO
from services.chamado_service import (
    adicionar_peca_chamado,
    assumir_chamado,
    calcular_segundos_decorridos,
    cancelar_chamado,
    concluir_chamado,
    listar_chamados_em_andamento,
    listar_historico_chamados,
    obter_chamado_detalhado,
    remover_peca_chamado,
    salvar_progresso_laudo,
)
from services.equipamento_service import listar_pecas
from ui_components import (
    esc,
    formatar_data_br,
    formatar_duracao_hm,
    formatar_relogio_hms,
    navegar_para,
    renderizar_topbar,
    rotulo_amigavel,
    selo_html,
)


def _calcular_espera_min(abertura_str: str | None, inicio_str: str | None) -> int:
    if not abertura_str or not inicio_str:
        return 0
    try:
        a = datetime.strptime(str(abertura_str).replace("T", " ").split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        b = datetime.strptime(str(inicio_str).replace("T", " ").split(".")[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return max(0, int(round((b - a).total_seconds() / 60.0)))
    except Exception:
        return 0


def _render_cronometro_box(ch: dict) -> None:
    status = ch["status_chamado"]
    espera_min = _calcular_espera_min(ch.get("data_hora_abertura"), ch.get("data_hora_inicio_atendimento"))

    if status == "EM_ANDAMENTO":
        seg_reparo = calcular_segundos_decorridos(ch.get("data_hora_inicio_atendimento"))
        seg_parada = calcular_segundos_decorridos(ch.get("data_hora_abertura"))
        relogio_txt = formatar_relogio_hms(seg_reparo)
        sub_txt = "Tempo desde o início do atendimento"
        parada_txt = formatar_duracao_hm(round(seg_parada / 60.0))
    elif status == "ABERTO":
        seg_parada = calcular_segundos_decorridos(ch.get("data_hora_abertura"))
        relogio_txt = "00:00:00"
        sub_txt = "Aguardando técnico assumir a OS"
        parada_txt = formatar_duracao_hm(round(seg_parada / 60.0))
        espera_min = int(round(seg_parada / 60.0))
    else:
        dt_total = int(ch.get("downtime_minutos") or 0)
        reparo_min = max(0, dt_total - espera_min)
        relogio_txt = formatar_duracao_hm(reparo_min)
        sub_txt = "Tempo total de reparo"
        parada_txt = formatar_duracao_hm(dt_total)

    st.markdown(
        f"""
        <div class="os-cronometro">
          <div>
            <div class="rotulo">Cronômetro de reparo</div>
            <div class="relogio-os">{esc(relogio_txt)}</div>
            <div class="sub">{esc(sub_txt)}</div>
          </div>
          <div class="divisor"></div>
          <div style="display:grid;gap:14px">
            <div class="mini">Downtime acumulado<strong>{esc(parada_txt)}</strong></div>
            <div class="mini">Espera até atendimento<strong>{esc(formatar_duracao_hm(espera_min))}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    """Renderiza a tela de Ordem de Serviço (A.renderOS do telas-tecnico.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    # Lista de OS em andamento + recentes para permitir seleção ou inspeção de qualquer OS
    em_andamento = listar_chamados_em_andamento()
    todos = listar_historico_chamados()
    opcoes_os = [c["id"] for c in em_andamento] + [
        c["id"] for c in todos if c["id"] not in {x["id"] for x in em_andamento}
    ]

    if not opcoes_os:
        renderizar_topbar("Ordem de serviço", "Nenhuma OS cadastrada")
        st.markdown(
            '<div class="card"><div class="vazio"><strong>Nenhuma OS selecionada</strong>Escolha um chamado na fila de chamados ou no painel de máquinas.</div></div>',
            unsafe_allow_html=True,
        )
        return

    pre_id = st.session_state.get("os_selecionada_id")
    idx_os = opcoes_os.index(pre_id) if pre_id in opcoes_os else 0

    mapa_resumo = {c["id"]: c for c in todos}
    os_id_sel = st.selectbox(
        "Selecionar Ordem de Serviço",
        options=opcoes_os,
        index=idx_os,
        format_func=lambda cid: (
            f"OS #{cid} · {mapa_resumo[cid]['equipamento_tag']} — {mapa_resumo[cid]['equipamento_nome']} "
            f"[{rotulo_amigavel(mapa_resumo[cid]['status_chamado'])}]"
        ),
        label_visibility="collapsed",
    )
    st.session_state["os_selecionada_id"] = os_id_sel

    ch = obter_chamado_detalhado(os_id_sel)
    if not ch:
        st.error("Ordem de serviço não encontrada.")
        return

    renderizar_topbar("Ordem de serviço", f"OS #{ch['id']}")

    pode_operar = usuario["perfil"] in ("TECNICO", "GESTOR")
    eh_responsavel = ch.get("tecnico_responsavel_id") == usuario["id"]
    eh_gestor = usuario["perfil"] == "GESTOR"
    editavel = ch["status_chamado"] == "EM_ANDAMENTO"
    pode_editar = editavel and pode_operar and (eh_responsavel or eh_gestor)

    # 1. Topo da OS (.os-topo: Cronômetro à esquerda + Dados da OS à direita)
    col_cron, col_dados = st.columns([1.35, 1])

    with col_cron:
        if editavel and hasattr(st, "fragment"):
            @st.fragment(run_every="2s")
            def _crono_vivo() -> None:
                _render_cronometro_box(ch)

            _crono_vivo()
        else:
            _render_cronometro_box(ch)

    with col_dados:
        dt_calc_str = (
            formatar_duracao_hm(ch["downtime_minutos"])
            if ch.get("downtime_minutos") is not None
            else "em andamento"
        )
        st.markdown(
            f"""
            <div class="card">
              <div class="card-cabecalho">
                <h2>Dados da OS</h2>
                <div class="acao">
                  {selo_html(ch['status_chamado'])}
                  {selo_html(ch['prioridade'])}
                </div>
              </div>
              <div class="card-corpo">
                <div class="dados-lista">
                  <div class="linha"><span class="r">Máquina</span><span class="v">{esc(ch['equipamento_tag'])} — {esc(ch['equipamento_nome'])}</span></div>
                  <div class="linha"><span class="r">Estação / posto</span><span class="v">{esc(ch['setor'])} · {esc(ch.get('posto_trabalho') or 'Posto 01')}</span></div>
                  <div class="linha"><span class="r">Tipo de manutenção</span><span class="v">{esc(rotulo_amigavel(ch['tipo_manutencao']))}</span></div>
                  <div class="linha"><span class="r">Operador que abriu</span><span class="v">{esc(ch.get('operador_nome') or '—')}</span></div>
                  <div class="linha"><span class="r">Técnico responsável</span><span class="v">{esc(ch.get('tecnico_nome') or 'Aguardando')}</span></div>
                  <div class="linha"><span class="r">Abertura</span><span class="v">{esc(formatar_data_br(ch.get('data_hora_abertura')))}</span></div>
                  <div class="linha"><span class="r">Início do atendimento</span><span class="v">{esc(formatar_data_br(ch.get('data_hora_inicio_atendimento')))}</span></div>
                  <div class="linha"><span class="r">Fim do atendimento</span><span class="v">{esc(formatar_data_br(ch.get('data_hora_fim_atendimento')))}</span></div>
                  <div class="linha"><span class="r">Downtime calculado</span><span class="v">{esc(dt_calc_str)}</span></div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Relato do operador + Diagnóstico técnico (grid-2)
    col_relato, col_diag = st.columns(2)

    with col_relato:
        st.markdown(
            f"""
            <div class="card">
              <div class="card-cabecalho"><h2>Relato do operador</h2></div>
              <div class="card-corpo">
                <p style="margin:0; line-height:1.6; color:var(--cinza-900);">{esc(ch['descricao_falha'])}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_diag:
        st.markdown(
            """
            <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
              <div class="card-cabecalho"><h2>Diagnóstico técnico</h2></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if pode_editar:
            causas_opcoes = list(CAUSAS_RAIZ_PADRAO)
            causa_atual = ch.get("causa_raiz") or ""
            if causa_atual and causa_atual not in causas_opcoes:
                causas_opcoes.insert(0, causa_atual)
            idx_causa = causas_opcoes.index(causa_atual) if causa_atual in causas_opcoes else 0
            idx_tipo = (
                TIPOS_MANUTENCAO.index(ch["tipo_manutencao"])
                if ch.get("tipo_manutencao") in TIPOS_MANUTENCAO
                else 0
            )

            diag_val = st.text_area(
                "Diagnóstico *",
                value=ch.get("diagnostico_tecnico") or "",
                placeholder="Descreva a análise técnica e a intervenção realizada.",
                key=f"diag_txt_{ch['id']}",
            )
            cd1, cd2 = st.columns(2)
            with cd1:
                causa_val = st.selectbox(
                    "Causa raiz *",
                    options=causas_opcoes,
                    index=idx_causa,
                    key=f"causa_sel_{ch['id']}",
                )
            with cd2:
                tipo_val = st.selectbox(
                    "Tipo de manutenção",
                    options=TIPOS_MANUTENCAO,
                    index=idx_tipo,
                    format_func=rotulo_amigavel,
                    key=f"tipo_sel_{ch['id']}",
                )
            if st.button("Salvar diagnóstico", type="secondary", key=f"btn_save_diag_{ch['id']}"):
                salvar_progresso_laudo(ch["id"], diag_val, causa_val, tipo_val)
                st.toast("Diagnóstico registrado.", icon="✅")
                st.rerun()
        else:
            st.markdown(
                f"""
                <div class="card" style="border-top:0; border-radius:0 0 10px 10px;">
                  <div class="card-corpo">
                    <p style="margin:0 0 12px; line-height:1.6;">{esc(ch.get('diagnostico_tecnico') or 'Ainda não registrado.')}</p>
                    <div class="dados-lista">
                      <div class="linha"><span class="r">Causa raiz</span><span class="v">{esc(ch.get('causa_raiz') or '—')}</span></div>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # 3. Card: Peças substituídas
    pecas_os = ch.get("pecas_trocadas") or []
    st.markdown(
        f"""
        <div class="card" style="margin-bottom:8px;">
          <div class="card-cabecalho">
            <h2>Peças substituídas</h2>
            <div class="acao">{len(pecas_os)} item(ns)</div>
          </div>
          <div class="card-corpo" style="padding-bottom:10px;">
            {"".join(
                f'<div class="peca-item"><span class="cod">{esc(p["codigo_peca"])}</span>'
                f'<span class="nome">{esc(p["nome"])}</span>'
                f'<span class="qtd">{p["quantidade"]:g} {esc(p["unidade"])}</span></div>'
                for p in pecas_os
            ) or '<div class="vazio" style="padding:12px;">Nenhuma peça registrada nesta OS.</div>'}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if pode_editar:
        if pecas_os:
            cols_rem = st.columns(min(4, len(pecas_os)))
            for i_p, p in enumerate(pecas_os):
                with cols_rem[i_p % len(cols_rem)]:
                    if st.button(
                        f"× Remover {p['codigo_peca']}",
                        key=f"rem_p_{p['id']}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        remover_peca_chamado(p["id"])
                        st.toast("Peça removida da OS.", icon="🗑️")
                        st.rerun()

        catalogo = listar_pecas(apenas_ativas=True)
        if catalogo:
            mapa_cat = {p["id"]: p for p in catalogo}
            cp1, cp2, cp3 = st.columns([3, 1, 1])
            with cp1:
                peca_sel_id = st.selectbox(
                    "Peça do catálogo",
                    options=[p["id"] for p in catalogo],
                    format_func=lambda pid: f"{mapa_cat[pid]['codigo_peca']} — {mapa_cat[pid]['nome']} ({mapa_cat[pid]['unidade_medida']})",
                    key=f"add_peca_sel_{ch['id']}",
                )
            with cp2:
                qtd_in = st.number_input(
                    "Qtd.",
                    min_value=0.1,
                    step=1.0,
                    value=1.0,
                    key=f"add_peca_qtd_{ch['id']}",
                )
            with cp3:
                st.write("")
                st.write("")
                if st.button("Adicionar", type="primary", use_container_width=True, key=f"btn_add_p_{ch['id']}"):
                    try:
                        adicionar_peca_chamado(ch["id"], peca_sel_id, qtd_in)
                        st.toast("Peça registrada na OS.", icon="✅")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    # 4. Card: Ações da ordem de serviço
    st.markdown(
        """
        <div class="card" style="margin-top:14px; margin-bottom:8px;">
          <div class="card-cabecalho"><h2>Ações da ordem de serviço</h2></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if ch["status_chamado"] in ("CONCLUIDO", "CANCELADO"):
        st.markdown(
            f"""
            <div class="aviso-info aviso-ok">
              <span>✓</span>
              <div>OS <strong>{esc(rotulo_amigavel(ch['status_chamado']).lower())}</strong> em
              {esc(formatar_data_br(ch.get('data_hora_fim_atendimento')))}.
              Downtime registrado: <strong>{esc(formatar_duracao_hm(ch.get('downtime_minutos') or 0))}</strong>.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ca1, ca2, ca3 = st.columns([1.4, 1.1, 1])
    with ca1:
        if ch["status_chamado"] == "ABERTO" and pode_operar:
            if st.button("Assumir esta OS", type="primary", use_container_width=True):
                try:
                    assumir_chamado(ch["id"], usuario["id"])
                    st.toast(f"OS #{ch['id']} assumida!", icon="🔧")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        elif pode_editar:
            if st.button("Concluir OS e liberar máquina", type="primary", use_container_width=True):
                try:
                    diag_final = st.session_state.get(f"diag_txt_{ch['id']}", ch.get("diagnostico_tecnico") or "")
                    causa_final = st.session_state.get(f"causa_sel_{ch['id']}", ch.get("causa_raiz") or "")
                    tipo_final = st.session_state.get(f"tipo_sel_{ch['id']}", ch.get("tipo_manutencao") or "CORRETIVA")
                    res = concluir_chamado(
                        chamado_id=ch["id"],
                        usuario_id=usuario["id"],
                        diagnostico_tecnico=diag_final,
                        causa_raiz=causa_final,
                        tipo_manutencao=tipo_final,
                    )
                    st.toast(
                        f"OS #{ch['id']} concluída! Downtime: {res['downtime_minutos']} min.",
                        icon="✅",
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with ca2:
        if pode_editar:
            if st.button("Cancelar OS", type="secondary", use_container_width=True):
                try:
                    cancelar_chamado(ch["id"], usuario["id"], "Cancelado na tela da OS")
                    st.toast(f"OS #{ch['id']} cancelada.", icon="⚠️")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with ca3:
        if st.button("Voltar à fila", type="secondary", use_container_width=True):
            navegar_para("fila_chamados")

    if not pode_operar:
        st.markdown(
            """
            <div class="aviso-info aviso-alerta" style="margin-top:10px;">
              <span>!</span>
              <div>Seu perfil acompanha a OS em modo somente leitura. Assumir e concluir são ações do técnico.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    render()
