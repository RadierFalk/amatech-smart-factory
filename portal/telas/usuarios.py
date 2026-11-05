"""
Módulo 5: Gestão Central de Usuários e Controle de Acessos (USR / RBAC).
Permite ao Administrador criar contas corporativas, alterar personas,
ativar/desativar colaboradores, redefinir senhas e auditar a Matriz de Permissões.
"""
from typing import Any

import streamlit as st

from identidade import amatech
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
    """Interface administrativa de gerenciamento de identidades corporativas do ERP."""
    amatech.cabecalho(
        "ERP",
        [
            ("Turno", amatech.turno_atual()),
            ("Módulo", "Gestão de Usuários (USR)"),
            (
                usuario_logado["perfil"],
                f"{amatech.esc(usuario_logado['nome'])} · <span class='am-codigo'>{amatech.esc(usuario_logado['matricula'])}</span>",
            ),
        ],
    )

    col_t, col_b = st.columns([4, 1.2])
    with col_t:
        amatech.titulo(
            "Gestão de Usuários e Controle de Acessos (RBAC)",
            "Administração centralizada de credenciais corporativas, personas e permissões de acesso aos 5 módulos do ERP",
            breadcrumb="ERP AMATECH · ADMINISTRAÇÃO",
        )
    with col_b:
        if st.button("⬅️ Seletor de Módulos", icon=":material/apps:", width="stretch", key="usr_btn_voltar_hub"):
            st.session_state["modulo_ativo"] = None
            st.rerun()

    usuarios = listar_usuarios()

    # Métricas gerais com cartões AMATECH
    m1, m2, m3, m4 = st.columns(4)
    total = len(usuarios)
    ativos = sum(1 for u in usuarios if u["ativo"])
    admins = sum(1 for u in usuarios if u["perfil"] == ADMINISTRADOR)
    operacao = sum(1 for u in usuarios if u["perfil"] != ADMINISTRADOR)

    with m1:
        amatech.cartao("Total de Colaboradores", str(total), "Contas registradas no ERP")
    with m2:
        amatech.cartao("Usuários Ativos", str(ativos), f"{total - ativos} inativo(s)", "ok")
    with m3:
        amatech.cartao("Administradores", str(admins), "Acesso total aos 5 módulos")
    with m4:
        amatech.cartao("Personas Operacionais", str(operacao), "Acesso segmentado por função")

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    aba_lista, aba_novo, aba_matriz = st.tabs([
        ":material/group: Colaboradores Cadastrados",
        ":material/person_add: Novo Colaborador",
        ":material/security: Matriz de Acesso por Persona",
    ])

    with aba_lista:
        for u in usuarios:
            with st.container(border=True):
                c_info, c_perf, c_status, c_acoes = st.columns([3, 2.2, 1.3, 2], vertical_alignment="center")

                modulos_u = [m.sigla for m in modulos_permitidos(u)]
                modulos_badge = " · ".join(modulos_u) if modulos_u else "Nenhum"

                with c_info:
                    st.markdown(f"**{amatech.esc(u['nome'])}**")
                    st.caption(f"Matrícula: `{u['matricula']}` | Módulos: **{modulos_badge}**")

                with c_perf:
                    st.markdown(f"**Persona:** `{u['perfil']}`")

                with c_status:
                    if u["ativo"]:
                        st.markdown(amatech.etiqueta("Ativo", "ok"), unsafe_allow_html=True)
                    else:
                        st.markdown(amatech.etiqueta("Inativo", "critico"), unsafe_allow_html=True)

                with c_acoes:
                    with st.popover("Gerenciar Conta", icon=":material/settings:"):
                        st.markdown(f"**Gerenciar Conta: {u['matricula']}**")

                        novo_perfil = st.selectbox(
                            "Alterar Persona:",
                            options=PERFIS_TODOS,
                            index=PERFIS_TODOS.index(u["perfil"]) if u["perfil"] in PERFIS_TODOS else 0,
                            key=f"perf_{u['id']}",
                        )
                        if st.button("Salvar Perfil", key=f"btn_perf_{u['id']}", type="primary"):
                            sucesso, msg = alterar_perfil(u["id"], novo_perfil)
                            if sucesso:
                                st.success(msg)
                                st.rerun()

                        st.markdown("---")

                        rotulo_ativo = "Desativar Conta" if u["ativo"] else "Ativar Conta"
                        if st.button(rotulo_ativo, key=f"btn_ativ_{u['id']}"):
                            sucesso, msg = alternar_ativo(u["id"])
                            if sucesso:
                                st.success(msg)
                                st.rerun()

                        st.markdown("---")

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
            matricula = st.text_input(
                "Matrícula Funcional:",
                value=sugestao_mat,
                help="Gerada automaticamente pelo prefixo da persona ou personalizada.",
            )
            senha = st.text_input("Senha Inicial:", value="amatech1234", type="password")

            st.caption(f"**Escopo da Persona Selecionada:** {DESCRICAO_PERSONAS[perfil]}")

            enviar = st.form_submit_button("Cadastrar Colaborador", type="primary", icon=":material/save:")
            if enviar:
                sucesso, msg, _ = criar_usuario(nome, perfil, senha, matricula)
                if sucesso:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with aba_matriz:
        st.markdown("#### Matriz Corporativa de Acessos aos Módulos do ERP")
        st.markdown(
            """
            Cada colaborador autenticado enxerga no **Seletor de Módulos** exclusivamente os módulos em que sua persona
            possui atribuições operacionais ou gerenciais:
            """
        )

        dados_tabela = []
        for p in PERFIS_TODOS:
            mock_u = {"perfil": p}
            mods = {m.sigla for m in modulos_permitidos(mock_u)}
            dados_tabela.append({
                "Persona / Cargo": p,
                "Rastreabilidade (RAS)": "✅ Permitido" if "RAS" in mods else "❌ Oculto",
                "Qualidade (QLD)": "✅ Permitido" if "QLD" in mods else "❌ Oculto",
                "Manutenção (MNT)": "✅ Permitido" if "MNT" in mods else "❌ Oculto",
                "Dashboard (DSH)": "✅ Permitido" if "DSH" in mods else "❌ Oculto",
                "Gestão Usuários (USR)": "✅ Permitido" if "USR" in mods else "❌ Oculto",
                "Total Módulos": len(mods),
            })

        st.dataframe(dados_tabela, use_container_width=True, hide_index=True)
