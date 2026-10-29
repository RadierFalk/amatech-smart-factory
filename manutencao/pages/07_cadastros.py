"""
Tela de Cadastros (F14, F15, F16, RN07).
Replica as 4 abas (Máquinas, Estações, Peças, Usuários), tabelas .tabela,
cards de Estações com vínculo 1:N e modais/formulários de edição e inativação lógica
do projeto amatech-manutencao.
"""
import streamlit as st

from config import ESTACOES_FLUXO, PERFIS_USUARIO, SETORES_PADRAO
from services.auth_service import (
    alternar_status_usuario,
    criar_usuario,
    listar_usuarios,
)
from services.equipamento_service import (
    alternar_status_ativo_equipamento,
    alternar_status_ativo_peca,
    atualizar_equipamento,
    criar_equipamento,
    criar_peca,
    listar_equipamentos,
    listar_pecas,
)
from ui_components import esc, renderizar_topbar, rotulo_amigavel, selo_html


def render() -> None:
    """Renderiza a tela de Cadastros (A.renderCadastros do telas-gestor.js)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    if usuario.get("perfil") != "GESTOR":
        st.error("Acesso restrito (RN01): Apenas usuários com perfil Gestor podem gerenciar cadastros.")
        return

    renderizar_topbar("Cadastros", "Estações, máquinas, peças e usuários do sistema")

    tab_maq, tab_est, tab_pecas, tab_users = st.tabs(
        ["Máquinas", "Estações", "Peças", "Usuários"]
    )

    # =========================================================================
    # ABA 1: MÁQUINAS
    # =========================================================================
    with tab_maq:
        maquinas = listar_equipamentos(apenas_ativos=False)
        linhas_m = ""
        for m in maquinas:
            ordem_e = ESTACOES_FLUXO.get(m["setor"], (3, "SMT", ""))[0]
            sit_html = (
                '<span style="color:var(--verde);font-weight:600">Ativa</span>'
                if m["ativo"]
                else '<span style="color:var(--cinza-500);font-weight:600">Inativa</span>'
            )
            linhas_m += (
                f'<tr>'
                f'<td class="mono"><strong>{esc(m["codigo_tag"])}</strong></td>'
                f'<td>{esc(m["nome"])}</td>'
                f'<td>{ordem_e}. {esc(m["setor"])}</td>'
                f'<td>{esc(m.get("posto_trabalho") or "—")}</td>'
                f'<td>{selo_html(m["status_operacional"])}</td>'
                f'<td>{sit_html}</td>'
                f'</tr>'
            )

        st.markdown(
            f"""
            <div class="card">
              <div class="card-cabecalho">
                <h2>Máquinas cadastradas</h2>
                <div class="acao">{len(maquinas)} equipamento(s)</div>
              </div>
              <div class="tabela-wrap">
                <table class="tabela">
                  <thead>
                    <tr>
                      <th>TAG</th><th>Máquina</th><th>Estação</th><th>Posto</th><th>Estado</th><th>Situação</th>
                    </tr>
                  </thead>
                  <tbody>{linhas_m}</tbody>
                </table>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c_novo_m, c_edit_m = st.columns(2)
        with c_novo_m:
            with st.expander("＋ Nova máquina", expanded=False):
                with st.form("form_cad_nova_maq", clear_on_submit=True):
                    f1, f2 = st.columns(2)
                    with f1:
                        tag_in = st.text_input("TAG de identificação *", placeholder="Ex.: SMT-05")
                    with f2:
                        posto_in = st.text_input("Posto de trabalho", value="Posto 01")
                    nome_in = st.text_input("Nome da máquina *", placeholder="Ex.: Insersora Automática de Componentes")
                    setor_in = st.selectbox("Estação (etapa do processo) *", options=SETORES_PADRAO)
                    if st.form_submit_button("Cadastrar máquina", type="primary", use_container_width=True):
                        try:
                            criar_equipamento(tag_in, nome_in, setor_in, posto_in)
                            st.toast("Máquina cadastrada com sucesso.", icon="✅")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

        with c_edit_m:
            with st.expander("✎ Editar / Inativar / Reativar máquina (RN07)", expanded=False):
                if maquinas:
                    mapa_m = {m["id"]: m for m in maquinas}
                    m_id_sel = st.selectbox(
                        "Selecionar máquina",
                        options=[m["id"] for m in maquinas],
                        format_func=lambda mid: f"{mapa_m[mid]['codigo_tag']} — {mapa_m[mid]['nome']} ({'Ativa' if mapa_m[mid]['ativo'] else 'Inativa'})",
                    )
                    m_obj = mapa_m[m_id_sel]
                    with st.form("form_cad_edit_maq"):
                        ed_nome = st.text_input("Nome da máquina *", value=m_obj["nome"])
                        idx_s = SETORES_PADRAO.index(m_obj["setor"]) if m_obj["setor"] in SETORES_PADRAO else 0
                        ed_setor = st.selectbox("Estação *", options=SETORES_PADRAO, index=idx_s)
                        ed_posto = st.text_input("Posto de trabalho", value=m_obj.get("posto_trabalho") or "Posto 01")
                        if st.form_submit_button("Salvar alterações", type="primary", use_container_width=True):
                            try:
                                atualizar_equipamento(m_id_sel, ed_nome, ed_setor, ed_posto)
                                st.toast("Máquina atualizada.", icon="✅")
                                st.rerun()
                            except Exception as exc:
                                st.error(str(exc))

                    novo_est = not bool(m_obj["ativo"])
                    lbl_m = "Reativar máquina" if novo_est else "Inativar máquina (exclusão lógica)"
                    if st.button(lbl_m, key="btn_inativar_maq", type="secondary", use_container_width=True):
                        try:
                            alternar_status_ativo_equipamento(m_id_sel, novo_est)
                            st.toast("Situação da máquina atualizada.", icon="✅")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

    # =========================================================================
    # ABA 2: ESTAÇÕES DO PROCESSO PRODUTIVO
    # =========================================================================
    with tab_est:
        maquinas_todas = listar_equipamentos(apenas_ativos=False)
        por_setor: dict[str, list[dict]] = {}
        for m in maquinas_todas:
            por_setor.setdefault(m["setor"], []).append(m)

        estacoes_lista = []
        vistos = set()
        for nome_est, (ordem, cod, desc) in sorted(ESTACOES_FLUXO.items(), key=lambda x: x[1][0]):
            if cod in vistos and nome_est == "Linha SMT" and "SMT" in por_setor:
                continue
            vistos.add(cod)
            maqs_est = por_setor.get(nome_est, [])
            estacoes_lista.append((ordem, cod, nome_est, desc, maqs_est))

        st.markdown(
            f"""
            <div class="card">
              <div class="card-cabecalho">
                <h2>Estações do processo produtivo</h2>
                <div class="acao">{len(estacoes_lista)} estações · vínculo 1:N com as máquinas</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cols_est = st.columns(3)
        for idx, (ordem, cod, nome_est, desc, maqs_est) in enumerate(estacoes_lista):
            with cols_est[idx % 3]:
                indisp = sum(1 for m in maqs_est if m["status_operacional"] != "OPERACIONAL" and m["ativo"])
                indisp_html = (
                    f' · <span style="color:var(--vermelho);font-weight:600">{indisp} fora de operação</span>'
                    if indisp
                    else ""
                )
                tags_html = (
                    "".join(
                        f'<span class="tag" style="margin-right:4px">{esc(m["codigo_tag"])}</span>'
                        for m in maqs_est
                    )
                    or "Sem máquinas"
                )
                st.markdown(
                    f"""
                    <article class="maquina-card" style="border-left-color:var(--azul); margin-bottom:12px;">
                      <div style="display:flex;align-items:center;gap:8px">
                        <span style="background:var(--navy);color:#fff;font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:4px">ETAPA {ordem}</span>
                        <span class="tag">{esc(cod)}</span>
                      </div>
                      <div class="nome">{esc(nome_est)}</div>
                      <div class="meta">{esc(desc)}</div>
                      <div class="meta"><strong>{len(maqs_est)}</strong> máquina(s) vinculada(s){indisp_html}</div>
                      <div class="meta" style="font-size:11px">{tags_html}</div>
                    </article>
                    """,
                    unsafe_allow_html=True,
                )

    # =========================================================================
    # ABA 3: CATÁLOGO DE PEÇAS
    # =========================================================================
    with tab_pecas:
        pecas = listar_pecas(apenas_ativas=False)
        linhas_p = ""
        for p in pecas:
            sit_p = (
                '<span style="color:var(--verde);font-weight:600">Ativa</span>'
                if p["ativo"]
                else '<span style="color:var(--cinza-500);font-weight:600">Inativa</span>'
            )
            linhas_p += (
                f'<tr>'
                f'<td class="mono"><strong>{esc(p["codigo_peca"])}</strong></td>'
                f'<td>{esc(p["nome"])}</td>'
                f'<td>{esc(p["unidade_medida"])}</td>'
                f'<td>{sit_p}</td>'
                f'</tr>'
            )

        st.markdown(
            f"""
            <div class="card">
              <div class="card-cabecalho">
                <h2>Catálogo de peças</h2>
                <div class="acao">{len(pecas)} item(ns)</div>
              </div>
              <div class="tabela-wrap">
                <table class="tabela">
                  <thead>
                    <tr><th>Código</th><th>Peça</th><th>Unidade</th><th>Situação</th></tr>
                  </thead>
                  <tbody>{linhas_p}</tbody>
                </table>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cp_novo, cp_edit = st.columns(2)
        with cp_novo:
            with st.expander("＋ Nova peça", expanded=False):
                with st.form("form_cad_nova_peca", clear_on_submit=True):
                    cod_p = st.text_input("Código / PN *", placeholder="Ex.: PN-COR-101")
                    unid_p = st.selectbox("Unidade", options=["UN", "M", "KG", "KIT", "L"])
                    nome_p = st.text_input("Descrição *", placeholder="Ex.: Correia de transporte SMT")
                    if st.form_submit_button("Cadastrar", type="primary", use_container_width=True):
                        try:
                            criar_peca(cod_p, nome_p, unid_p)
                            st.toast("Peça cadastrada.", icon="✅")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

        with cp_edit:
            with st.expander("✎ Ativar / Inativar peça (RN07)", expanded=False):
                if pecas:
                    mapa_p = {p["id"]: p for p in pecas}
                    pid_sel = st.selectbox(
                        "Selecionar peça",
                        options=[p["id"] for p in pecas],
                        format_func=lambda pid: f"{mapa_p[pid]['codigo_peca']} — {mapa_p[pid]['nome']} ({'Ativa' if mapa_p[pid]['ativo'] else 'Inativa'})",
                    )
                    p_obj = mapa_p[pid_sel]
                    novo_p = not bool(p_obj["ativo"])
                    if st.button(
                        "Reativar peça" if novo_p else "Inativar peça",
                        key="btn_toggle_p_cad",
                        type="secondary",
                        use_container_width=True,
                    ):
                        alternar_status_ativo_peca(pid_sel, novo_p)
                        st.toast("Peça atualizada.", icon="✅")
                        st.rerun()

    # =========================================================================
    # ABA 4: USUÁRIOS E PERFIS DE ACESSO
    # =========================================================================
    with tab_users:
        usuarios = listar_usuarios(apenas_ativos=False)
        linhas_u = ""
        for u in usuarios:
            sit_u = (
                '<span style="color:var(--verde);font-weight:600">Ativo</span>'
                if u["ativo"]
                else '<span style="color:var(--vermelho);font-weight:600">Inativo</span>'
            )
            linhas_u += (
                f'<tr>'
                f'<td class="mono"><strong>{esc(u["matricula"])}</strong></td>'
                f'<td>{esc(u["nome"])}</td>'
                f'<td>{selo_html(u["perfil"])}</td>'
                f'<td>{sit_u}</td>'
                f'</tr>'
            )

        st.markdown(
            f"""
            <div class="card">
              <div class="card-cabecalho">
                <h2>Usuários e perfis de acesso</h2>
                <div class="acao">Operador · Técnico · Gestor (RN01)</div>
              </div>
              <div class="tabela-wrap">
                <table class="tabela">
                  <thead>
                    <tr><th>Matrícula</th><th>Nome</th><th>Perfil</th><th>Acesso</th></tr>
                  </thead>
                  <tbody>{linhas_u}</tbody>
                </table>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cu_novo, cu_edit = st.columns(2)
        with cu_novo:
            with st.expander("＋ Novo usuário", expanded=False):
                with st.form("form_cad_novo_user", clear_on_submit=True):
                    nome_u = st.text_input("Nome completo *")
                    mat_u = st.text_input("Matrícula *", placeholder="Ex.: OP-10240")
                    perf_u = st.selectbox("Perfil *", options=PERFIS_USUARIO, format_func=rotulo_amigavel)
                    st.caption("Operador: painel e chamados · Técnico: + fila e OS · Gestor: acesso total.")
                    senha_u = st.text_input("Senha *", type="password", value="123456")
                    if st.form_submit_button("Cadastrar", type="primary", use_container_width=True):
                        try:
                            criar_usuario(nome_u, mat_u, senha_u, perf_u)
                            st.toast("Usuário cadastrado.", icon="✅")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))

        with cu_edit:
            with st.expander("✎ Ativar / Inativar usuário (RN01 / RN07)", expanded=False):
                if usuarios:
                    mapa_u = {u["id"]: u for u in usuarios}
                    uid_sel = st.selectbox(
                        "Selecionar usuário",
                        options=[u["id"] for u in usuarios],
                        format_func=lambda uid: f"{mapa_u[uid]['matricula']} — {mapa_u[uid]['nome']} ({'Ativo' if mapa_u[uid]['ativo'] else 'Inativo'})",
                    )
                    u_obj = mapa_u[uid_sel]
                    novo_u = not bool(u_obj["ativo"])
                    if st.button(
                        "Reativar usuário" if novo_u else "Inativar usuário",
                        key="btn_toggle_u_cad",
                        type="secondary",
                        use_container_width=True,
                    ):
                        if uid_sel == usuario["id"] and not novo_u:
                            st.error("Você não pode inativar sua própria conta.")
                        else:
                            alternar_status_usuario(uid_sel, novo_u)
                            st.toast("Usuário atualizado.", icon="✅")
                            st.rerun()


if __name__ == "__main__":
    render()
