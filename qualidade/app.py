import sys
from pathlib import Path

import streamlit as st

# Identidade visual comum aos quatro sistemas (pasta identidade/ na raiz do repositório)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from identidade import amatech  # noqa: E402

import banco  # noqa: E402
import integracao  # noqa: E402
import migracao  # noqa: E402
import permissoes  # noqa: E402
import sessao  # noqa: E402
from telas.dashboard import mostrar_dashboard  # noqa: E402
from telas.historico_ocorrencias import mostrar_historico_ocorrencias  # noqa: E402
from telas.login import mostrar_login  # noqa: E402
from telas.registro_ocorrencia import mostrar_registro_ocorrencia  # noqa: E402
from telas.usuarios import mostrar_usuarios  # noqa: E402


# A API (api.py) roda como um processo separado:  python -m uvicorn api:app --port 5000
# Ela usa a chave X-API-Key e não depende do login da tela.
banco.preparar_banco()

amatech.configurar_pagina("QLD", layout="wide")
amatech.aplicar_estilos()
amatech.estilo_matplotlib()


# ============================================================
# BANCO: contas de acesso (backup + migração, só quando há algo a fazer)
# ============================================================

@st.cache_resource(show_spinner=False)
def preparar_contas():
    return migracao.migrar()


try:
    preparar_contas()
except Exception as erro:
    st.error(f"Não foi possível preparar as contas de acesso: {erro}")
    st.stop()


# ============================================================
# LOGIN: sem sessão válida, só a tela de entrada aparece
# ============================================================

usuario = sessao.usuario_atual()

if usuario is None:
    mostrar_login()
    st.stop()


# ============================================================
# BARRA LATERAL
# ============================================================

st.sidebar.title("Controle da Qualidade")

st.sidebar.markdown(
    f"**{usuario['nome']}**  \n"
    f"Matrícula: {usuario['matricula']}  \n"
    f"Perfil: {usuario['perfil']}"
)

if st.sidebar.button("Sair"):
    sessao.encerrar()
    st.rerun()

paginas = permissoes.paginas_permitidas(usuario)

pagina = st.sidebar.radio(
    "Navegação",
    paginas
)


# Notebooks da Rastreabilidade e máquinas da Manutenção: busca uma vez por sessão e quando o usuário pedir
if permissoes.tem_permissao(usuario, permissoes.ATUALIZAR_CADASTROS):
    atualizar_cadastros = st.sidebar.button("Atualizar cadastros dos setores", icon=":material/sync:", width="stretch")

    if atualizar_cadastros or "cadastros_sincronizados" not in st.session_state:
        st.session_state["cadastros_sincronizados"] = integracao.sincronizar_cadastros()

    with st.sidebar.expander("Integração com os setores"):
        for tipo, mensagem in st.session_state.get("cadastros_sincronizados", []):
            if tipo == "sucesso":
                st.caption(mensagem)
            else:
                st.warning(mensagem)


amatech.cabecalho("QLD", [("Turno", amatech.turno_atual())])


# ============================================================
# PÁGINAS (só as permitidas ao perfil aparecem no menu)
# ============================================================

if pagina == "Dashboard":
    mostrar_dashboard()

elif pagina == "Registrar ocorrência":
    mostrar_registro_ocorrencia(usuario)

elif pagina == "Histórico":
    mostrar_historico_ocorrencias(usuario)

elif pagina == "Usuários":
    mostrar_usuarios(usuario)
