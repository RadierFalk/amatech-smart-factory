import streamlit as st

import banco
import integracao
import migracao
import permissoes
import sessao
from telas.dashboard import mostrar_dashboard
from telas.login import mostrar_login
from telas.registro_ocorrencia import mostrar_registro_ocorrencia
from telas.historico_ocorrencias import mostrar_historico_ocorrencias
from telas.usuarios import mostrar_usuarios


# A API (api.py) roda como um processo separado:  python -m uvicorn api:app --port 5000
# Ela usa a chave X-API-Key e não depende do login da tela.
banco.preparar_banco()


st.set_page_config(
    page_title="Controle da Qualidade",
    page_icon="📋",
    layout="wide"
)


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
    atualizar_cadastros = st.sidebar.button("Atualizar cadastros dos setores")

    if atualizar_cadastros or "cadastros_sincronizados" not in st.session_state:
        st.session_state["cadastros_sincronizados"] = integracao.sincronizar_cadastros()

    with st.sidebar.expander("Integração com os setores"):
        for tipo, mensagem in st.session_state["cadastros_sincronizados"]:
            if tipo == "sucesso":
                st.caption(mensagem)
            else:
                st.warning(mensagem)


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
