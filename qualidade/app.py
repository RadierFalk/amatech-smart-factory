import streamlit as st

import banco
import integracao
from telas.dashboard import mostrar_dashboard
from telas.registro_ocorrencia import mostrar_registro_ocorrencia
from telas.historico_ocorrencias import mostrar_historico_ocorrencias


# A API (api.py) roda como um processo separado:  python -m uvicorn api:app --port 5000
banco.preparar_banco()


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