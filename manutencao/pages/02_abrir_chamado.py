"""
Telas do Operador: Abrir chamado (F03) e Meus chamados (F04).
Replica o layout grid 2:1, cards, tabela de máquinas com chamado ativo e guia "Como funciona"
do projeto de referência amatech-manutencao.
"""
from datetime import datetime
import streamlit as st

from config import ESTACOES_FLUXO, PRIORIDADES
from services.chamado_service import abrir_chamado, listar_historico_chamados
from services.equipamento_service import listar_equipamentos
from ui_components import (
    esc,
    formatar_data_br,
    formatar_duracao_hm,
    kpi_html,
    navegar_para,
    renderizar_topbar,
    rotulo_amigavel,
    selo_html,
)


def render_meus_chamados() -> None:
    """Renderiza a tela 'Meus chamados' (A.renderMeusChamados do telas-operador.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_topbar("Meus chamados", "Acompanhamento das ocorrências que você registrou")

    chamados = listar_historico_chamados(
        operador_id=usuario["id"] if usuario["perfil"] == "OPERADOR" else None
    )
    abertos = [c for c in chamados if c["status_chamado"] == "ABERTO"]
    em_andamento = [c for c in chamados if c["status_chamado"] == "EM_ANDAMENTO"]
    concluidos = [c for c in chamados if c["status_chamado"] == "CONCLUIDO"]
    ativos = abertos + em_andamento

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            kpi_html("Chamados em aberto", str(len(abertos)), detalhe="Aguardando técnico", variante="azul"),
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            kpi_html("Em atendimento", str(len(em_andamento)), detalhe="Técnico já assumiu a OS", variante="amarelo"),
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            kpi_html("Concluídos", str(len(concluidos)), detalhe="Máquina liberada", variante="verde"),
            unsafe_allow_html=True,
        )

    if ativos:
        st.markdown(
            f"""
            <div class="aviso-info aviso-alerta">
              <span>!</span>
              <div>Você tem <strong>{len(ativos)}</strong> chamado(s) em andamento. Acompanhe abaixo a OS e o tempo de parada.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    linhas_html = ""
    for c in chamados[:80]:
        prio_cls = f"prioridade-{str(c['prioridade']).lower()}"
        tempo_str = (
            formatar_duracao_hm(c["downtime_minutos"])
            if c.get("downtime_minutos") is not None
            else formatar_duracao_hm(c.get("tempo_parado_min") or 0)
        )
        linhas_html += (
            f'<tr class="{prio_cls}">'
            f'<td class="mono"><strong>#{c["id"]}</strong></td>'
            f'<td>{esc(formatar_data_br(c["data_hora_abertura"]))}</td>'
            f'<td>{esc(c["equipamento_tag"])} — {esc(c["equipamento_nome"])}</td>'
            f'<td>{esc(c["setor"])}</td>'
            f'<td>{selo_html(c["prioridade"])}</td>'
            f'<td>{selo_html(c["status_chamado"])}</td>'
            f'<td>{esc(c.get("tecnico_nome") or "—")}</td>'
            f'<td class="num">{esc(tempo_str)}</td>'
            f'</tr>'
        )

    if not linhas_html:
        linhas_html = (
            '<tr><td colspan="8"><div class="vazio"><strong>Nenhum chamado registrado</strong>'
            "Abra o primeiro chamado no painel de máquinas.</div></td></tr>"
        )

    st.markdown(
        f"""
        <div class="card">
          <div class="card-cabecalho"><h2>Histórico dos meus registros</h2></div>
          <div class="tabela-wrap">
            <table class="tabela">
              <thead>
                <tr>
                  <th>OS</th><th>Abertura</th><th>Máquina</th><th>Estação</th><th>Prioridade</th>
                  <th>Status</th><th>Técnico</th><th class="num">Tempo parado</th>
                </tr>
              </thead>
              <tbody>{linhas_html}</tbody>
            </table>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    """Renderiza a tela 'Abrir chamado' (A.renderAbrirChamado do telas-operador.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    renderizar_topbar("Abrir chamado", "Registro rápido de parada de máquina")

    todas_maquinas = listar_equipamentos(apenas_ativos=True)
    disponiveis = sorted(
        [m for m in todas_maquinas if m["status_operacional"] == "OPERACIONAL" and not m.get("os_ativa_id")],
        key=lambda x: (ESTACOES_FLUXO.get(x["setor"], (99, "", ""))[0], x["codigo_tag"]),
    )
    bloqueadas = [m for m in todas_maquinas if m["status_operacional"] != "OPERACIONAL" or m.get("os_ativa_id")]

    col_esq, col_dir = st.columns([2, 1])

    with col_esq:
        st.markdown(
            """
            <div class="card" style="margin-bottom:0; border-bottom:0; border-radius:10px 10px 0 0;">
              <div class="card-cabecalho"><h2>Dados do chamado</h2></div>
              <div class="card-corpo" style="padding-bottom:4px;">
                <div class="aviso-info">
                  <span>⏱</span>
                  <div><strong>Passo 1:</strong> selecione a máquina parada. Setor e posto são preenchidos
                  automaticamente a partir da estação vinculada. <strong>Passo 2:</strong> escolha a prioridade
                  e descreva a falha. Ao confirmar, o sistema grava o timestamp e bloqueia a máquina.</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not disponiveis:
            st.warning("Todas as máquinas ativas já possuem chamado em andamento no momento.")
        else:
            opcoes_ids = [m["id"] for m in disponiveis]
            mapa_disp = {m["id"]: m for m in disponiveis}
            pre_id = st.session_state.get("equipamento_preselecionado_id")
            idx_sel = opcoes_ids.index(pre_id) if pre_id in opcoes_ids else 0

            maq_id = st.selectbox(
                "Máquina parada *",
                options=opcoes_ids,
                index=idx_sel,
                format_func=lambda mid: (
                    f"{ESTACOES_FLUXO.get(mapa_disp[mid]['setor'], (3, '', ''))[0]}. "
                    f"{mapa_disp[mid]['setor']} · {mapa_disp[mid]['codigo_tag']} — {mapa_disp[mid]['nome']}"
                ),
            )
            st.caption(
                f"{len(disponiveis)} máquina(s) disponível(is) para abertura · "
                f"{len(bloqueadas)} já com chamado ativo"
            )

            m_sel = mapa_disp[maq_id]
            ordem_est = ESTACOES_FLUXO.get(m_sel["setor"], (3, "", ""))[0]

            c_est, c_posto = st.columns(2)
            with c_est:
                st.text_input("Estação", value=f"{ordem_est}. {m_sel['setor']}", disabled=True)
            with c_posto:
                st.text_input(
                    "Posto / estado atual",
                    value=f"{m_sel.get('posto_trabalho') or 'Posto 01'} · Funcionando",
                    disabled=True,
                )

            with st.form("form_abrir_chamado_ref", clear_on_submit=False):
                prioridade_sel = st.radio(
                    "Prioridade *",
                    options=PRIORIDADES,
                    index=1,
                    horizontal=True,
                    format_func=rotulo_amigavel,
                )

                c_tipo, c_dt = st.columns(2)
                with c_tipo:
                    opcoes_tipo = [
                        ("CORRETIVA", "Corretiva (falha já ocorreu)"),
                        ("PREVENTIVA", "Preventiva (programada)"),
                    ]
                    tipo_sel = st.selectbox(
                        "Tipo de manutenção",
                        options=[x[0] for x in opcoes_tipo],
                        format_func=lambda k: dict(opcoes_tipo)[k],
                    )
                with c_dt:
                    st.text_input(
                        "Data/hora da abertura",
                        value=f"{datetime.now().strftime('%d/%m/%Y %H:%M')} (gerada pelo servidor)",
                        disabled=True,
                    )

                desc_falha = st.text_area(
                    "Descrição da falha *",
                    placeholder=(
                        "O que aconteceu com a máquina? Informe o sintoma observado, o produto/lote em "
                        "processo e se há risco de perda de material."
                    ),
                    height=105,
                )

                submeter = st.form_submit_button(
                    "Registrar chamado e parar máquina",
                    type="primary",
                    use_container_width=True,
                )

                if submeter:
                    try:
                        novo_id = abrir_chamado(
                            equipamento_id=maq_id,
                            operador_abertura_id=usuario["id"],
                            prioridade=prioridade_sel,
                            descricao_falha=desc_falha,
                            tipo_manutencao=tipo_sel,
                        )
                        st.toast(f"Chamado #{novo_id} registrado com sucesso!", icon="✅")
                        navegar_para("ordem_servico", os_selecionada_id=novo_id)
                    except Exception as exc:
                        st.error(str(exc))

    with col_dir:
        # Card 1: Máquinas com chamado ativo
        if bloqueadas:
            linhas_bloq = "".join(
                f'<tr>'
                f'<td class="mono"><strong>{esc(m["codigo_tag"])}</strong></td>'
                f'<td>{selo_html(m["status_operacional"])}</td>'
                f'<td class="num">OS #{m.get("os_ativa_id") or "—"}</td>'
                f'</tr>'
                for m in bloqueadas
            )
            corpo_bloq = f'<div class="tabela-wrap"><table class="tabela"><tbody>{linhas_bloq}</tbody></table></div>'
        else:
            corpo_bloq = '<div class="vazio">Nenhuma máquina parada no momento.</div>'

        st.markdown(
            f'<div class="card">'
            f'<div class="card-cabecalho"><h2>Máquinas com chamado ativo</h2></div>'
            f'<div class="card-corpo" style="padding:0">{corpo_bloq}</div>'
            f'</div>'
            f'<div class="card">'
            f'<div class="card-cabecalho"><h2>Como funciona</h2></div>'
            f'<div class="card-corpo">'
            f'<div class="dados-lista">'
            f'<div class="linha"><span class="r">1. Abertura</span><span class="v">Máquina → INDISPONÍVEL</span></div>'
            f'<div class="linha"><span class="r">2. Técnico assume</span><span class="v">Máquina → EM MANUTENÇÃO</span></div>'
            f'<div class="linha"><span class="r">3. Conclusão da OS</span><span class="v">Máquina → FUNCIONANDO</span></div>'
            f'<div class="linha"><span class="r">Downtime</span><span class="v">fim − abertura (automático)</span></div>'
            f'</div>'
            f'<div class="aviso-info aviso-alerta" style="margin-top:14px; margin-bottom:0;">'
            f'<span>!</span><div>Uma máquina não pode ter dois chamados ativos ao mesmo tempo (RN02).</div>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    render()
