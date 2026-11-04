import sys
from pathlib import Path

import streamlit as st

# Identidade visual comum aos quatro sistemas (pasta identidade/ na raiz do repositório)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from identidade import amatech  # noqa: E402

import banco  # noqa: E402
import integracao  # noqa: E402
from telas.dashboard import mostrar_dashboard  # noqa: E402
from telas.registro_ocorrencia import mostrar_registro_ocorrencia  # noqa: E402
from telas.historico_ocorrencias import mostrar_historico_ocorrencias  # noqa: E402


# A API (api.py) roda como um processo separado:  python -m uvicorn api:app --port 5000
banco.preparar_banco()


amatech.configurar_pagina("QLD", layout="wide")
amatech.aplicar_estilos()
amatech.estilo_matplotlib()


pagina = st.navigation([
    st.Page(mostrar_dashboard, title="Painel", icon=":material/dashboard:", default=True),
    st.Page(mostrar_registro_ocorrencia, title="Registrar ocorrência", icon=":material/add_circle:"),
    st.Page(mostrar_historico_ocorrencias, title="Histórico", icon=":material/history:"),
])


# Notebooks da Rastreabilidade e máquinas da Manutenção: busca uma vez por sessão e quando o usuário pedir
with st.sidebar:
    atualizar_cadastros = st.button("Atualizar cadastros dos setores", icon=":material/sync:", width="stretch")

if atualizar_cadastros or "cadastros_sincronizados" not in st.session_state:
    st.session_state["cadastros_sincronizados"] = integracao.sincronizar_cadastros()

with st.sidebar.expander("Integração com os setores"):
    for tipo, mensagem in st.session_state["cadastros_sincronizados"]:
        if tipo == "sucesso":
            st.caption(mensagem)
        else:
            st.warning(mensagem)


amatech.cabecalho("QLD", [("Turno", amatech.turno_atual())])
pagina.run()
