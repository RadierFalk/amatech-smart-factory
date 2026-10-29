"""Dashboard Industrial: entrada do sistema. Tela de login (T01) e menu de telas conforme o perfil (RF18, RF19).

Executar com:  streamlit run app.py
"""
import streamlit as st

from pages.comum import pode, usuario_logado
from servicos.autenticacao import ServicoAutenticacao

st.set_page_config(page_title="Dashboard Industrial · AMATECH", page_icon="🏭", layout="wide")

# Tela, título no menu e permissões que dão acesso a ela (basta uma)
TELAS = [
    ("pages/1_Painel.py", "Painel", ("painel",)),
    ("pages/2_Producao_e_metas.py", "Produção e metas", ("producao", "metas")),
    ("pages/3_Qualidade.py", "Qualidade", ("defeitos", "retrabalho")),
    ("pages/4_Paradas.py", "Paradas", ("paradas",)),
    ("pages/5_Perdas.py", "Perdas", ("perdas",)),
    ("pages/6_Importacao.py", "Importação", ("importacao",)),
    ("pages/7_Historico.py", "Histórico", ("historico",)),
    ("pages/8_Cadastros.py", "Cadastros", ("cadastros", "limites")),
    ("pages/9_Usuarios.py", "Usuários", ("usuarios",)),
]


def tela_login():
    """T01: login e senha. O menu só aparece depois do login."""
    _, centro, _ = st.columns([1, 1.2, 1])
    with centro:
        st.markdown("## AMATECH\n#### Dashboard Industrial")
        with st.form("login"):
            login = st.text_input("Login")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")
        if entrar:
            usuario = ServicoAutenticacao().autenticar(login, senha)
            if usuario is None:
                st.error("Login ou senha inválidos, ou usuário desativado.")
            else:
                st.session_state["usuario"] = usuario
                st.rerun()
        st.caption("Usuários de teste: admin/admin123, supervisor/super123, gestor/gestor123, "
                   "operador/oper123, inspetor/insp123, manutencao/manut123.")


def barra_lateral(usuario):
    with st.sidebar:
        st.markdown(f"**{usuario.nome}**  \n{usuario.perfil.nome}")


def sair():
    st.session_state.clear()
    st.rerun()


usuario = usuario_logado()
if usuario is None:
    st.navigation([st.Page(tela_login, title="Entrar", default=True)], position="hidden").run()
else:
    paginas = []
    for arquivo, titulo, funcoes in TELAS:
        if any(pode(f) for f in funcoes):
            if arquivo.endswith("Cadastros.py") and not pode("cadastros"):
                titulo = "Limites do semáforo"   # o Supervisor só ajusta os limites (T09, RN08)
            paginas.append(st.Page(arquivo, title=titulo))
    barra_lateral(usuario)
    pagina = st.navigation(paginas)
    with st.sidebar:
        st.divider()
        if st.button("Sair", width="stretch"):
            sair()
    pagina.run()
