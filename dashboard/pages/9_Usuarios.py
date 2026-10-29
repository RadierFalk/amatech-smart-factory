"""T10 Usuários (RF19). Administrador cria usuários, redefine senhas e ativa ou desativa contas."""
import streamlit as st

from pages.comum import data_br, exigir, mostrar_erro, opcoes, tabela
from servicos.autenticacao import ServicoAutenticacao
from servicos.erros import ErroValidacao

usuario = exigir("usuarios")
st.title("Usuários")

autenticacao = ServicoAutenticacao()
if "aviso_usuarios" in st.session_state:   # mensagem da ação anterior, que recarregou a tela
    st.success(st.session_state.pop("aviso_usuarios"))

usuarios = autenticacao.listar_usuarios()
for u in usuarios:
    u["situacao"] = "Ativo" if u["ativo"] else "Desativado"
    u["criado"] = data_br(u["criado_em"])
tabela(usuarios, {"nome": "Nome", "login": "Login", "perfil": "Perfil", "situacao": "Situação", "criado": "Criado em"})

novo, senha, ativo = st.tabs(["Novo usuário", "Redefinir senha", "Ativar ou desativar"])
with novo:
    with st.form("novo_usuario", clear_on_submit=True):
        c = st.columns(2)
        nome = c[0].text_input("Nome completo")
        login = c[1].text_input("Login")
        ids_perfil, rotulo_perfil = opcoes(autenticacao.listar_perfis(), "id_perfil", "nome")
        id_perfil = c[0].selectbox("Perfil", ids_perfil, format_func=rotulo_perfil)
        nova_senha = c[1].text_input("Senha inicial", type="password", help="Pelo menos 6 caracteres.")
        if st.form_submit_button("Criar usuário", type="primary"):
            try:
                autenticacao.criar_usuario(nome, login, id_perfil, nova_senha)
                st.session_state["aviso_usuarios"] = f"Usuário {login.strip().lower()} criado."
                st.rerun()
            except ErroValidacao as erro:
                mostrar_erro(erro)

ids_usuario, rotulo_usuario = opcoes(usuarios, "id_usuario", lambda u: f"{u['nome']} ({u['login']})")
with senha:
    with st.form("redefinir_senha", clear_on_submit=True):
        id_usuario = st.selectbox("Usuário", ids_usuario, format_func=rotulo_usuario)
        nova_senha = st.text_input("Nova senha", type="password", help="Pelo menos 6 caracteres.")
        if st.form_submit_button("Redefinir senha", type="primary"):
            try:
                autenticacao.redefinir_senha(id_usuario, nova_senha)
                st.success("Senha redefinida.")
            except ErroValidacao as erro:
                mostrar_erro(erro)
with ativo:
    id_usuario = st.selectbox("Usuário", ids_usuario, format_func=rotulo_usuario, key="usuario_ativo")
    atual = next(u for u in usuarios if u["id_usuario"] == id_usuario)
    if id_usuario == usuario.id:
        st.caption("Você não pode desativar a sua própria conta.")
    elif st.button("Desativar" if atual["ativo"] else "Ativar", type="primary"):
        autenticacao.alterar_ativo(id_usuario, not atual["ativo"])
        st.session_state["aviso_usuarios"] = f"Usuário {atual['login']} {'desativado' if atual['ativo'] else 'ativado'}."
        st.rerun()
    st.caption("Usuários são desativados, nunca apagados: assim não se perde quem lançou cada dado.")
