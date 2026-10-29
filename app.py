import threading

import streamlit as st

import integracao
from api import app as api_app
from telas.dashboard import mostrar_dashboard
from telas.registro_ocorrencia import mostrar_registro_ocorrencia
from telas.historico_ocorrencias import mostrar_historico_ocorrencias


def iniciar_api():
    api_app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False
    )


if "api_iniciada" not in st.session_state:
    thread_api = threading.Thread(
        target=iniciar_api,
        daemon=True
    )

    thread_api.start()

    st.session_state["api_iniciada"] = True


st.set_page_config(
    page_title="Controle da Qualidade",
    page_icon="📋",
    layout="wide"
)


st.sidebar.title("Controle da Qualidade")


pagina = st.sidebar.radio(
    "Navegação",
    [
        "Dashboard",
        "Registrar ocorrência",
        "Histórico"
    ]
)


# Notebooks da Rastreabilidade e máquinas da Manutenção: busca uma vez por sessão e quando o usuário pedir
atualizar_cadastros = st.sidebar.button("Atualizar cadastros dos setores")

if atualizar_cadastros or "cadastros_sincronizados" not in st.session_state:
    st.session_state["cadastros_sincronizados"] = integracao.sincronizar_cadastros()

with st.sidebar.expander("Integração com os setores"):
    for tipo, mensagem in st.session_state["cadastros_sincronizados"]:
        if tipo == "sucesso":
            st.caption(mensagem)
        else:
            st.warning(mensagem)


if pagina == "Dashboard":
    mostrar_dashboard()

elif pagina == "Registrar ocorrência":
    mostrar_registro_ocorrencia()

elif pagina == "Histórico":
    mostrar_historico_ocorrencias()