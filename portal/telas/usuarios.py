"""
Módulo 4: Gestão Central de Usuários e Acessos (IAM / RBAC).
Permite ao Administrador criar contas, alterar perfis/personas,
ativar/desativar colaboradores e redefinir credenciais.
"""
from typing import Any

import streamlit as st

from banco import (
    alterar_perfil,
    alternar_ativo,
    criar_usuario,
    listar_usuarios,
    proxima_matricula,
    redefinir_senha,
)
from permissoes import (
    ADMINISTRADOR,
    DESCRICAO_PERSONAS,
    PERFIS_TODOS,
    modulos_permitidos,
)


def mostrar_gestao_usuarios(usuario_logado: dict[str, Any]) -> None:
    """Interface administrativa de gerenciamento de identidades corporativas."""
    col_t, col_b = st.columns([4, 1])
    with col_t:
        st.markdown(
            """
            <h2 style="font-family: var(--font-display); font-size: 1.6rem; font-weight: 700; color: var(--tinta); margin: 0;">
                Módulo 4: Gestão de Usuários e Controle de Acessos (RBAC)
            </h2>
            <p style="color: var(--tinta-2); font-size: 0.95rem;">
                Administração centralizada de credenciais funcionais, personas e concessão de módulos.
            </p>
            """,
            unsafe_allow_html=True,
        )
    with col_b:
        if st.button("⬅️ Seletor de Módulos", icon=":material/arrow_back:", width="stretch"):
            st.session_state["modulo_ativo"] = None
            st.rerun()

    usuarios = listar_usuarios()

    # Métricas gerais
    m1, m2, m3, m4 = st.columns(4)
    total = len(usuarios)
    ativos = sum(1 for u in usuarios if u["ativo"])
    admins = sum(1 for u in usuarios if u["perfil"] == ADMINISTRADOR)
    operadores = sum(1 for u in usuarios if u["perfil"] != ADMINISTRADOR)

    with m1:
        st.metric("Total de Colaboradores", total)
    with m2:
        st.metric("Usuários Ativos", ativos)
    with m3:
        st.metric("Administradores", admins)
    with m4:
        st.metric("Usuários de Operação", operadores)

    st.markdown("---")

    # Abas: Lista de Usuários | Novo Usuário | Matriz de Permissões
    aba_lista, aba_novo, aba_matriz = st.tabs([
        ":material/group: Colaboradores Cadastrados",
        ":material/person_add: Novo Colaborador",
        ":material/security: Matriz de Acesso por Persona",
    ])

    with aba_lista:
        for u in usuarios:
            with st.container(border=True):
                c_info, c_perf, c_status, c_acoes = st.columns([3, 2, 1.5, 2.5], vertical_alignment="center")

                # Módulos aos quais este usuário tem acesso
                modulos_u = [m.sigla for m in modulos_permitidos(u)]
                modulos_badge = " · ".join(modulos_u) if modulos_u else "Nenhum"

                with c_info:
                    st.markdown(f"**{u['nome']}**")
                    st.caption(f"Matrícula: `{u['matricula']}` | Acessos: **{modulos_badge}**")

                with c_perf:
                    st.markdown(f"**Persona:** `{u['perfil']}`")

                with c_status:
                    if u["ativo"]:
                        st.markdown("<span style='color: green; font-weight: 600;'>● Ativo</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color: red; font-weight: 600;'>○ Inativo</span>", unsafe_allow_html=True)

                with c_acoes:
                    with st.popover("Gerenciar", icon=":material/settings:"):
                        st.markdown(f"**Gerenciar Conta: {u['matricula']}**")

                        # Trocar Perfil
                        novo_perfil = st.selectbox(
                            "Alterar Persona:",
                            options=PERFIS_TODOS,
                            index=PERFIS_TODOS.index(u["perfil"]) if u["perfil"] in PERFIS_TODOS else 0,
                            key=f"perf_{u['id']}",
                        )
                        if st.button("Salvar Perfil", key=f"btn_perf_{u['id']}"):
                            sucesso, msg = alterar_perfil(u["id"], novo_perfil)
                            if sucesso:
                                st.success(msg)
                                st.rerun()

                        st.markdown("---")

                        # Alternar Ativo/Inativo
                        rotulo_ativo = "Desativar Conta" if u["ativo"] else "Ativar Conta"
                        if st.button(rotulo_ativo, key=f"btn_ativ_{u['id']}"):
                            sucesso, msg = alternar_ativo(u["id"])
                            if sucesso:
                                st.success(msg)
                                st.rerun()

                        st.markdown("---")

                        # Redefinir Senha
                        nova_senha = st.text_input("Nova Senha:", type="password", key=f"pwd_{u['id']}")
                        if st.button("Redefinir Senha", key=f"btn_pwd_{u['id']}"):
                            sucesso, msg = redefinir_senha(u["id"], nova_senha)
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    with aba_novo:
        st.markdown("#### Cadastrar Novo Colaborador no ERP")
        with st.form("form_novo_usuario"):
            nome = st.text_input("Nome Completo:", placeholder="Ex: Roberto Alencar")
            perfil = st.selectbox("Perfil / Persona Operacional:", options=PERFIS_TODOS)
            sugestao_mat = proxima_matricula(perfil)
            matricula = st.text_input("Matrícula Funcional:", value=sugestao_mat, help="Gerada automaticamente ou personalizada.")
            senha = st.text_input("Senha Inicial:", value="amatech1234", type="password")

            st.caption(f"**Escopo da Persona Selecionada:** {DESCRICAO_PERSONAS[perfil]}")

            enviar = st.form_submit_button("Cadastrar Colaborador", type="primary", icon=":material/save:")
            if enviar:
                sucesso, msg, novo = criar_usuario(nome, perfil, senha, matricula)
                if sucesso:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with aba_matriz:
        st.markdown("#### Matriz Corporativa de Acessos aos Módulos")
        st.markdown(
            """
            Cada colaborador cadastrado herda as regras estritas da sua persona.
            A tabela abaixo demonstra quais módulos cada persona tem poder para visualizar e operar:
            """
        )

        dados_tabela = []
        for p in PERFIS_TODOS:
            mock_u = {"perfil": p}
            mods = {m.sigla for m in modulos_permitidos(mock_u)}
            dados_tabela.append({
                "Persona / Cargo": p,
                "Rastreabilidade (RAS)": "✅ Permitido" if "RAS" in mods else "❌ Bloqueado",
                "Qualidade (QLD)": "✅ Permitido" if "QLD" in mods else "❌ Bloqueado",
                "Manutenção (MNT)": "✅ Permitido" if "MNT" in mods else "❌ Bloqueado",
                "Gestão Usuários (IAM)": "✅ Permitido" if "IAM" in mods else "❌ Bloqueado",
                "Total Módulos": len(mods),
            })

        st.dataframe(dados_tabela, use_container_width=True, hide_index=True)
