"""
Tela 8: Cadastros do Sistema (F14, F15, F16, RN07).
Gerenciamento administrativo (com inativação lógica / Soft Delete) de:
- Equipamentos / Máquinas
- Catálogo de Peças Sobressalentes
- Usuários e Colaboradores
"""
import pandas as pd
import streamlit as st

from config import PERFIS_USUARIO, SETORES_PADRAO
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
from ui_components import renderizar_cabecalho


def render() -> None:
    """Renderiza a Tela 8: Cadastros do Sistema (exclusiva para Perfil Gestor)."""
    usuario = st.session_state.get("usuario_logado")
    if not usuario:
        st.warning("Realize login para acessar esta tela.")
        return

    if usuario.get("perfil") != "GESTOR":
        st.error("⛔ Acesso restrito (RN01): Apenas usuários com perfil GESTOR podem gerenciar cadastros.")
        return

    renderizar_cabecalho(
        "⚙️ Cadastros Mestres do Sistema",
        "Gestão de Equipamentos, Catálogo de Peças Sobressalentes e Colaboradores (com Soft Delete RN07)",
        f"Gestor: {usuario['nome']}",
    )

    tab_eq, tab_pecas, tab_users = st.tabs(
        [
            "🏭 Equipamentos / Máquinas (F14)",
            "🔩 Peças Sobressalentes (F16)",
            "👥 Usuários e Perfis (F15)",
        ]
    )

    # =========================================================================
    # ABA 1: EQUIPAMENTOS (F14)
    # =========================================================================
    with tab_eq:
        col_form_eq, col_list_eq = st.columns([1.1, 1.9])

        with col_form_eq:
            st.subheader("Novo Equipamento")
            with st.form("form_novo_equipamento", clear_on_submit=True):
                tag_eq = st.text_input("Código / TAG da Máquina *", placeholder="Ex: SMT-04")
                nome_eq = st.text_input(
                    "Nome / Descrição do Equipamento *",
                    placeholder="Ex: Insersora Pick & Place Linha 2",
                )
                setor_eq = st.selectbox("Setor Produtivo *", options=SETORES_PADRAO)
                posto_eq = st.text_input("Posto de Trabalho *", value="Posto 01")

                if st.form_submit_button("➕ Cadastrar Equipamento", type="primary", use_container_width=True):
                    try:
                        novo_id = criar_equipamento(tag_eq, nome_eq, setor_eq, posto_eq)
                        st.success(f"Equipamento '{tag_eq.upper()}' cadastrado com sucesso (ID {novo_id})!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

            st.divider()
            st.subheader("Editar / Ativar / Inativar Máquina (RN07)")
            todos_eq = listar_equipamentos(apenas_ativos=False)
            if todos_eq:
                mapa_todos_eq = {e["id"]: e for e in todos_eq}
                eq_sel_id = st.selectbox(
                    "Selecione o Equipamento para Editar/Inativar",
                    options=[e["id"] for e in todos_eq],
                    format_func=lambda eid: (
                        f"{mapa_todos_eq[eid]['codigo_tag']} — {mapa_todos_eq[eid]['nome']} "
                        f"({'ATIVO' if mapa_todos_eq[eid]['ativo'] else 'INATIVO'})"
                    ),
                    key="cad_select_eq",
                )
                eq_obj = mapa_todos_eq[eq_sel_id]

                with st.form("form_edit_equipamento"):
                    novo_nome = st.text_input("Nome do Equipamento", value=eq_obj["nome"])
                    idx_setor = (
                        SETORES_PADRAO.index(eq_obj["setor"])
                        if eq_obj["setor"] in SETORES_PADRAO
                        else 0
                    )
                    novo_setor = st.selectbox("Setor", options=SETORES_PADRAO, index=idx_setor)
                    novo_posto = st.text_input(
                        "Posto de Trabalho", value=eq_obj["posto_trabalho"] or "Posto 01"
                    )
                    if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                        try:
                            atualizar_equipamento(eq_sel_id, novo_nome, novo_setor, novo_posto)
                            st.success("Equipamento atualizado!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro: {exc}")

                novo_estado_eq = not bool(eq_obj["ativo"])
                label_btn_eq = (
                    "✅ Reativar Equipamento" if novo_estado_eq else "🚫 Inativar Equipamento (Soft Delete)"
                )
                if st.button(label_btn_eq, key="btn_toggle_eq", use_container_width=True):
                    try:
                        alternar_status_ativo_equipamento(eq_sel_id, novo_estado_eq)
                        st.success("Status do equipamento atualizado!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

        with col_list_eq:
            st.subheader("Máquinas Cadastradas no Parque Fabril")
            if todos_eq:
                df_eq = pd.DataFrame(todos_eq)[
                    [
                        "id",
                        "codigo_tag",
                        "nome",
                        "setor",
                        "posto_trabalho",
                        "status_operacional",
                        "ativo",
                    ]
                ].rename(
                    columns={
                        "id": "ID",
                        "codigo_tag": "TAG",
                        "nome": "Nome do Equipamento",
                        "setor": "Setor",
                        "posto_trabalho": "Posto",
                        "status_operacional": "Status Operacional",
                        "ativo": "Ativo",
                    }
                )
                st.dataframe(df_eq, use_container_width=True, hide_index=True, height=450)

    # =========================================================================
    # ABA 2: CATÁLOGO DE PEÇAS SOBRESSALENTES (F16)
    # =========================================================================
    with tab_pecas:
        col_form_p, col_list_p = st.columns([1.1, 1.9])
        todas_pecas = listar_pecas(apenas_ativas=False)

        with col_form_p:
            st.subheader("Nova Peça / Insumo")
            with st.form("form_nova_peca", clear_on_submit=True):
                cod_p = st.text_input("Part Number / Código da Peça *", placeholder="Ex: PN-MOT-220")
                nome_p = st.text_input(
                    "Descrição da Peça *", placeholder="Ex: Servo Motor Passo 24V Alimentador"
                )
                unid_p = st.selectbox("Unidade de Medida *", options=["UN", "PC", "PAR", "MT", "KG", "LT"])

                if st.form_submit_button("➕ Cadastrar Peça", type="primary", use_container_width=True):
                    try:
                        criar_peca(cod_p, nome_p, unid_p)
                        st.success(f"Peça '{cod_p.upper()}' cadastrada no catálogo!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

            st.divider()
            st.subheader("Ativar / Inativar Peça (RN07)")
            if todas_pecas:
                mapa_p = {p["id"]: p for p in todas_pecas}
                p_sel_id = st.selectbox(
                    "Selecione a Peça",
                    options=[p["id"] for p in todas_pecas],
                    format_func=lambda pid: (
                        f"{mapa_p[pid]['codigo_peca']} — {mapa_p[pid]['nome']} "
                        f"({'ATIVA' if mapa_p[pid]['ativo'] else 'INATIVA'})"
                    ),
                    key="cad_select_peca",
                )
                p_obj = mapa_p[p_sel_id]
                novo_estado_p = not bool(p_obj["ativo"])
                label_btn_p = "✅ Reativar Peça" if novo_estado_p else "🚫 Inativar Peça (Soft Delete)"
                if st.button(label_btn_p, key="btn_toggle_peca", use_container_width=True):
                    try:
                        alternar_status_ativo_peca(p_sel_id, novo_estado_p)
                        st.success("Status da peça atualizado!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

        with col_list_p:
            st.subheader("Catálogo de Peças Sobressalentes")
            if todas_pecas:
                df_p = pd.DataFrame(todas_pecas).rename(
                    columns={
                        "id": "ID",
                        "codigo_peca": "Part Number",
                        "nome": "Nome / Descrição",
                        "unidade_medida": "Unidade",
                        "ativo": "Ativa",
                    }
                )
                st.dataframe(df_p, use_container_width=True, hide_index=True, height=450)

    # =========================================================================
    # ABA 3: USUÁRIOS E COLABORADORES (F15)
    # =========================================================================
    with tab_users:
        col_form_u, col_list_u = st.columns([1.1, 1.9])
        todos_usuarios = listar_usuarios(apenas_ativos=False)

        with col_form_u:
            st.subheader("Novo Usuário / Colaborador")
            with st.form("form_novo_usuario", clear_on_submit=True):
                nome_u = st.text_input("Nome Completo *", placeholder="Ex: Ariadne Araújo Farias")
                mat_u = st.text_input("Matrícula *", placeholder="Ex: TEC-2005 ou OP-10240")
                perfil_u = st.selectbox("Perfil de Acesso (RBAC) *", options=PERFIS_USUARIO)
                senha_u = st.text_input("Senha Inicial *", value="123456", type="password")

                if st.form_submit_button("➕ Cadastrar Usuário", type="primary", use_container_width=True):
                    try:
                        criar_usuario(nome_u, mat_u, senha_u, perfil_u)
                        st.success(f"Usuário '{nome_u}' ({mat_u.upper()}) cadastrado com sucesso!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro: {exc}")

            st.divider()
            st.subheader("Ativar / Inativar Usuário (RN01 / RN07)")
            if todos_usuarios:
                mapa_u = {u["id"]: u for u in todos_usuarios}
                u_sel_id = st.selectbox(
                    "Selecione o Colaborador",
                    options=[u["id"] for u in todos_usuarios],
                    format_func=lambda uid: (
                        f"{mapa_u[uid]['matricula']} — {mapa_u[uid]['nome']} [{mapa_u[uid]['perfil']}] "
                        f"({'ATIVO' if mapa_u[uid]['ativo'] else 'INATIVO'})"
                    ),
                    key="cad_select_user",
                )
                u_obj = mapa_u[u_sel_id]
                novo_estado_u = not bool(u_obj["ativo"])
                label_btn_u = (
                    "✅ Reativar Usuário" if novo_estado_u else "🚫 Inativar Usuário (Bloqueia Login)"
                )
                if st.button(label_btn_u, key="btn_toggle_user", use_container_width=True):
                    if u_sel_id == usuario["id"] and not novo_estado_u:
                        st.error("Você não pode inativar sua própria conta logada.")
                    else:
                        try:
                            alternar_status_usuario(u_sel_id, novo_estado_u)
                            st.success("Status do usuário atualizado!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro: {exc}")

        with col_list_u:
            st.subheader("Colaboradores Cadastrados")
            if todos_usuarios:
                df_u = pd.DataFrame(todos_usuarios).rename(
                    columns={
                        "id": "ID",
                        "nome": "Nome Completo",
                        "matricula": "Matrícula",
                        "perfil": "Perfil RBAC",
                        "ativo": "Ativo",
                        "criado_em": "Data Cadastro",
                    }
                )
                df_u["Ativo"] = df_u["Ativo"].astype(bool)
                st.dataframe(df_u, use_container_width=True, hide_index=True, height=450)


if __name__ == "__main__":
    render()
