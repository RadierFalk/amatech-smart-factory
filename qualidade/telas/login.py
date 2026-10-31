import streamlit as st

import autenticacao
import sessao


def mostrar_login():
    _, centro, _ = st.columns([1, 1.2, 1])

    with centro:
        st.markdown("## AMATECH")
        st.title("Sistema de Controle da Qualidade")
        st.caption("Entre com a sua matrícula e a sua senha.")

        aviso = st.session_state.pop(sessao.CHAVE_AVISO, None)

        if aviso:
            st.info(aviso)

        # Sem "key" nos campos: a senha não fica no st.session_state
        with st.form("form_login"):
            matricula = st.text_input("Matrícula", placeholder="Ex.: ADM-0001")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary")

        st.markdown("""
        ---
        **Acessos para demonstração**

        | Perfil | Matrícula |
        |---|---|
        | Administrador | `ADM-0001` |
        | Operador | `OPE-0001` |
        | Almoxarife | `ALM-0001` |
        | Inspetor de Qualidade | `QUA-0001` |

        **Senha para todas as contas:** `amatech1234`
        """)

        if entrar:
            usuario = autenticacao.autenticar(matricula, senha)

            if usuario is None:
                st.error("Matrícula ou senha inválida.")
            else:
                sessao.iniciar(usuario)
                st.rerun()