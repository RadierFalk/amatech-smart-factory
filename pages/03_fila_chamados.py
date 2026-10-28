"""
Telas do Técnico: Fila de chamados (F05, F06) e Manutenção Preventiva (F10).
Replica os contadores superiores, tabelas estilizadas (.tabela com faixa lateral de prioridade)
e programação de preventivas do projeto amatech-manutencao.
"""
import streamlit as st

from services.chamado_service import (
    abrir_chamado,
    assumir_chamado,
    listar_chamados_em_andamento,
    listar_fila_chamados,
    listar_historico_chamados,
)
from services.equipamento_service import listar_equipamentos
from ui_components import (
    esc,
    formatar_data_br,
    formatar_duracao_hm,
    navegar_para,
    renderizar_topbar,
    rotulo_amigavel,
    selo_html,
)


def render_preventiva() -> None:
    """Renderiza a tela de Manutenção Preventiva (A.renderPreventiva do telas-tecnico.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_topbar("Manutenção preventiva", "Programação de intervenções planejadas")

    todas_maq = listar_equipamentos(apenas_ativos=True)
    disponiveis = [m for m in todas_maq if not m.get("os_ativa_id")]
    preventivas = listar_historico_chamados(tipo_manutencao="PREVENTIVA")
    todos_chamados = listar_historico_chamados()
    total_corretivas = max(1, sum(1 for c in todos_chamados if c["tipo_manutencao"] == "CORRETIVA"))

    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.markdown(
            """
            <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
              <div class="card-cabecalho"><h2>Programar preventiva</h2></div>
              <div class="card-corpo" style="padding-bottom:4px;">
                <div class="aviso-info">
                  <span>i</span>
                  <div>A preventiva é registrada como OS do tipo <strong>PREVENTIVA</strong> sem parar a máquina
                  no momento do agendamento. A máquina só muda de estado quando o técnico assumir a OS.</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("form_programar_preventiva", clear_on_submit=True):
            opcoes_ids = [m["id"] for m in disponiveis]
            mapa_m = {m["id"]: m for m in disponiveis}
            maq_id = st.selectbox(
                "Máquina *",
                options=opcoes_ids,
                format_func=lambda mid: f"{mapa_m[mid]['codigo_tag']} — {mapa_m[mid]['nome']} ({mapa_m[mid]['setor']})",
            ) if opcoes_ids else None

            prio = st.selectbox(
                "Prioridade",
                options=["BAIXA", "MEDIA", "ALTA"],
                index=1,
                format_func=rotulo_amigavel,
            )
            plano = st.text_area(
                "Plano de manutenção",
                placeholder="Ex.: limpeza do forno, troca de filtros e verificação de sensores conforme plano trimestral.",
            )
            btn_prog = st.form_submit_button("Programar preventiva", type="primary")
            if btn_prog:
                if not maq_id:
                    st.warning("Nenhuma máquina disponível sem OS ativa.")
                else:
                    try:
                        texto_desc = plano.strip() or "Manutenção preventiva programada conforme plano de manutenção do ativo."
                        novo_id = abrir_chamado(
                            equipamento_id=maq_id,
                            operador_abertura_id=usuario["id"],
                            prioridade=prio,
                            descricao_falha=texto_desc,
                            tipo_manutencao="PREVENTIVA",
                            parar_maquina=False,
                        )
                        st.toast(f"Preventiva OS #{novo_id} programada com sucesso!", icon="✅")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    with col_dir:
        concluidas = sum(1 for r in preventivas if r["status_chamado"] == "CONCLUIDO")
        aguardando = sum(1 for r in preventivas if r["status_chamado"] == "ABERTO")
        st.markdown(
            f"""
            <div class="card">
              <div class="card-cabecalho"><h2>Indicadores de preventiva</h2></div>
              <div class="card-corpo">
                <div class="dados-lista">
                  <div class="linha"><span class="r">Preventivas registradas</span><span class="v">{len(preventivas)}</span></div>
                  <div class="linha"><span class="r">Concluídas</span><span class="v">{concluidas}</span></div>
                  <div class="linha"><span class="r">Aguardando atendimento</span><span class="v">{aguardando}</span></div>
                  <div class="linha"><span class="r">Proporção preventiva / corretiva</span><span class="v">{len(preventivas)} / {total_corretivas}</span></div>
                </div>
                <div class="aviso-info aviso-alerta" style="margin-top:16px; margin-bottom:0;">
                  <span>!</span>
                  <div>Referência de mercado: quanto maior a proporção de preventivas, menor o downtime
                  corretivo. É o argumento central do projeto para a diretoria.</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    linhas_prev = ""
    for r in preventivas:
        dt_str = formatar_duracao_hm(r["downtime_minutos"]) if r.get("downtime_minutos") is not None else "—"
        linhas_prev += f"""
        <tr>
          <td class="mono"><strong>#{r['id']}</strong></td>
          <td>{esc(r['equipamento_tag'])} — {esc(r['equipamento_nome'])}</td>
          <td>{esc(r['setor'])}</td>
          <td>{selo_html(r['status_chamado'])}</td>
          <td>{esc(formatar_data_br(r['data_hora_abertura']))}</td>
          <td>{esc(r.get('tecnico_nome') or '—')}</td>
          <td class="num">{esc(dt_str)}</td>
        </tr>
        """
    if not linhas_prev:
        linhas_prev = '<tr><td colspan="7"><div class="vazio">Nenhuma preventiva registrada.</div></td></tr>'

    st.markdown(
        f"""
        <div class="card" style="margin-top:16px;">
          <div class="card-cabecalho"><h2>Preventivas programadas</h2></div>
          <div class="tabela-wrap">
            <table class="tabela">
              <thead>
                <tr>
                  <th>OS</th><th>Máquina</th><th>Estação</th><th>Status</th><th>Abertura</th><th>Técnico</th><th class="num">Downtime</th>
                </tr>
              </thead>
              <tbody>{linhas_prev}</tbody>
            </table>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    """Renderiza a Fila de Chamados Técnicos (A.renderFila do telas-tecnico.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_topbar(
        "Fila de chamados",
        "Chamados abertos ordenados por prioridade e tempo de espera",
    )

    abertos = listar_fila_chamados()
    em_andamento = listar_chamados_em_andamento()
    todos = listar_historico_chamados()
    qtd_concluidos = sum(1 for c in todos if c["status_chamado"] == "CONCLUIDO")
    qtd_cancelados = sum(1 for c in todos if c["status_chamado"] == "CANCELADO")

    # Contadores no estilo .contadores + botão Atualizar
    col_cnt, col_btn = st.columns([4, 1])
    with col_cnt:
        st.markdown(
            f"""
            <div class="contadores">
              <div class="contador destaque"><div class="n">{len(abertos)}</div><div class="r">Aguardando técnico</div></div>
              <div class="contador"><div class="n">{len(em_andamento)}</div><div class="r">Em atendimento</div></div>
              <div class="contador"><div class="n">{qtd_concluidos}</div><div class="r">Concluídos</div></div>
              <div class="contador"><div class="n">{qtd_cancelados}</div><div class="r">Cancelados</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("↻ Atualizar fila", type="secondary", use_container_width=True):
            st.rerun()

    # Card 1: Chamados aguardando atendimento
    linhas_abertos_html = ""
    for ch in abertos:
        prio_cls = f"prioridade-{str(ch['prioridade']).lower()}"
        linhas_abertos_html += f"""
        <tr class="{prio_cls}">
          <td class="mono"><strong>#{ch['id']}</strong></td>
          <td><strong>{esc(ch['equipamento_tag'])}</strong><div style="font-size:11.5px;color:var(--cinza-500)">{esc(ch['equipamento_nome'])}</div></td>
          <td>{esc(ch['setor'])}<div style="font-size:11.5px;color:var(--cinza-500)">{esc(ch.get('posto_trabalho') or '')}</div></td>
          <td>{selo_html(ch['prioridade'])}<div style="margin-top:4px">{selo_html(ch['tipo_manutencao'])}</div></td>
          <td>{esc(ch['descricao_falha'])}</td>
          <td>{esc(ch.get('operador_nome') or '—')}</td>
          <td class="num"><strong>{esc(formatar_duracao_hm(ch['tempo_espera_min']))}</strong></td>
        </tr>
        """

    if not linhas_abertos_html:
        linhas_abertos_html = (
            '<tr><td colspan="7"><div class="vazio"><strong>Nenhum chamado aguardando</strong>'
            "Todas as ocorrências foram assumidas.</div></td></tr>"
        )

    st.markdown(
        f"""
        <div class="card">
          <div class="card-cabecalho">
            <h2>Chamados aguardando atendimento</h2>
            <div class="acao">Ordenados por prioridade e, em empate, por tempo de espera</div>
          </div>
          <div class="tabela-wrap">
            <table class="tabela">
              <thead>
                <tr>
                  <th>OS</th><th>Máquina</th><th>Estação / posto</th><th>Prioridade</th>
                  <th>Descrição da falha</th><th>Operador</th><th class="num">Parada há</th>
                </tr>
              </thead>
              <tbody>{linhas_abertos_html}</tbody>
            </table>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Botões rápidos para assumir qualquer chamado aberto
    if abertos and usuario["perfil"] in ("TECNICO", "GESTOR"):
        cols_assumir = st.columns(min(4, len(abertos)))
        for idx, ch in enumerate(abertos):
            with cols_assumir[idx % len(cols_assumir)]:
                if st.button(
                    f"Assumir OS #{ch['id']} ({ch['equipamento_tag']})",
                    key=f"btn_assumir_fila_{ch['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    try:
                        assumir_chamado(chamado_id=ch["id"], tecnico_id=usuario["id"])
                        st.toast(f"OS #{ch['id']} assumida com sucesso!", icon="🔧")
                        navegar_para("ordem_servico", os_selecionada_id=ch["id"])
                    except Exception as exc:
                        st.error(str(exc))

    # Card 2: Ordens de serviço em andamento
    linhas_and_html = ""
    for ch in em_andamento:
        prio_cls = f"prioridade-{str(ch['prioridade']).lower()}"
        linhas_and_html += f"""
        <tr class="{prio_cls}">
          <td class="mono"><strong>#{ch['id']}</strong></td>
          <td><strong>{esc(ch['equipamento_tag'])}</strong><div style="font-size:11.5px;color:var(--cinza-500)">{esc(ch['equipamento_nome'])}</div></td>
          <td>{esc(ch['setor'])}</td>
          <td>{selo_html(ch['prioridade'])}</td>
          <td>{esc(ch.get('tecnico_nome') or '—')}</td>
          <td>{esc(formatar_data_br(ch.get('data_hora_inicio_atendimento')))}</td>
          <td class="num"><strong>{esc(formatar_duracao_hm(ch['tempo_total_min']))}</strong></td>
        </tr>
        """

    if not linhas_and_html:
        linhas_and_html = (
            '<tr><td colspan="7"><div class="vazio">Nenhuma OS em atendimento no momento.</div></td></tr>'
        )

    st.markdown(
        f"""
        <div class="card" style="margin-top:16px;">
          <div class="card-cabecalho"><h2>Ordens de serviço em andamento</h2></div>
          <div class="tabela-wrap">
            <table class="tabela">
              <thead>
                <tr>
                  <th>OS</th><th>Máquina</th><th>Estação</th><th>Prioridade</th>
                  <th>Técnico</th><th>Início do atendimento</th><th class="num">Parada há</th>
                </tr>
              </thead>
              <tbody>{linhas_and_html}</tbody>
            </table>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if em_andamento:
        cols_abrir = st.columns(min(4, len(em_andamento)))
        for idx, ch in enumerate(em_andamento):
            with cols_abrir[idx % len(cols_abrir)]:
                if st.button(
                    f"Abrir OS #{ch['id']} ({ch['equipamento_tag']})",
                    key=f"btn_abrir_and_{ch['id']}",
                    type="secondary",
                    use_container_width=True,
                ):
                    navegar_para("ordem_servico", os_selecionada_id=ch["id"])


if __name__ == "__main__":
    render()
