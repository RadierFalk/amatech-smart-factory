import streamlit as st

import autenticacao
import banco
import permissoes


CHAVE_AVISO = "_aviso_usuarios"


# ============================================================
# JANELA: NOVO USUÁRIO
# ============================================================

@st.dialog("Novo usuário")
def janela_novo_usuario(ator):
    st.caption("A matrícula é gerada automaticamente a partir do tipo de usuário.")

    nome = st.text_input("Nome do usuário", placeholder="Nome completo")

    perfil = st.selectbox(
        "Tipo de usuário",
        options=permissoes.PERFIS,
        index=None,
        placeholder="Selecione o tipo de usuário"
    )

    if perfil:
        st.info(permissoes.DESCRICAO_PERFIL[perfil])
        st.write(f"Matrícula que será criada: **{autenticacao.previsao_matricula(perfil)}**")

    senha = st.text_input(
        "Senha inicial",
        type="password",
        help=f"Mínimo de {autenticacao.TAMANHO_MINIMO_SENHA} caracteres."
    )

    confirmacao = st.text_input("Confirmar a senha", type="password")

    col1, col2 = st.columns(2)

    with col1:
        criar = st.button("Criar usuário", type="primary")

    with col2:
        cancelar = st.button("Cancelar")

    if cancelar:
        st.rerun()

    if criar:
        if not perfil:
            st.error("Selecione o tipo de usuário.")
            return

        if senha != confirmacao:
            st.error("A confirmação da senha não confere.")
            return

        try:
            novo = autenticacao.criar_usuario(ator, nome, perfil, senha)
        except (ValueError, permissoes.PermissaoNegada) as erro:
            st.error(str(erro))
            return

        st.session_state[CHAVE_AVISO] = (
            f"Usuário criado: {novo['nome']} · matrícula {novo['matricula']} · {novo['perfil']}."
        )
        st.rerun()


# ============================================================
# TELA
# ============================================================

def mostrar_usuarios(usuario):
    if not permissoes.tem_permissao(usuario, permissoes.GERENCIAR_USUARIOS):
        st.error("Seu perfil não tem permissão para acessar esta página.")
        return

    st.title("Usuários")
    st.caption("Crie usuários e gerencie o acesso ao Sistema de Controle da Qualidade.")

    aviso = st.session_state.pop(CHAVE_AVISO, None)

    if aviso:
        st.success(aviso)

    if st.button("Novo usuário", type="primary"):
        janela_novo_usuario(usuario)

    contas = banco.listar_contas()

    # ========================================================
    # LISTA
    # ========================================================

    st.subheader("Contas")

    linhas = []

    for conta in contas:
        if conta["matricula"] is None:
            situacao = "Sem acesso (somente histórico)"
        elif conta["ativo"]:
            situacao = "Ativa"
        else:
            situacao = "Inativa"

        linhas.append({
            "Matrícula": conta["matricula"] or "—",
            "Nome": conta["nome_usuario"],
            "Perfil": conta["perfil_usuario"],
            "Situação": situacao
        })

    st.dataframe(linhas, hide_index=True)

    # ========================================================
    # GERENCIAR UMA CONTA
    # ========================================================

    gerenciaveis = [conta for conta in contas if conta["matricula"] is not None]

    if not gerenciaveis:
        return

    st.subheader("Gerenciar conta")

    opcoes = {
        f"{conta['matricula']} · {conta['nome_usuario']}": conta
        for conta in gerenciaveis
    }

    escolhida = st.selectbox("Usuário", options=list(opcoes.keys()))
    conta = opcoes[escolhida]
    eh_voce = conta["id_usuario"] == usuario["id_usuario"]

    st.write(f"Perfil atual: **{conta['perfil_usuario']}** · Situação: **{'Ativa' if conta['ativo'] else 'Inativa'}**")

    if eh_voce:
        st.caption("Esta é a sua conta: não é possível alterar o seu perfil nem desativá-la.")

    # ---- perfil
    col1, col2 = st.columns([3, 1])

    with col1:
        perfis = permissoes.PERFIS
        novo_perfil = st.selectbox(
            "Perfil",
            options=perfis,
            index=perfis.index(conta["perfil_usuario"]) if conta["perfil_usuario"] in perfis else 0,
            disabled=eh_voce,
            key=f"perfil_{conta['id_usuario']}"
        )

    with col2:
        st.write("")
        st.write("")
        salvar_perfil = st.button("Salvar perfil", disabled=eh_voce)

    if salvar_perfil:
        try:
            autenticacao.alterar_perfil(usuario, conta["id_usuario"], novo_perfil)
        except (ValueError, permissoes.PermissaoNegada) as erro:
            st.error(str(erro))
        else:
            st.session_state[CHAVE_AVISO] = "Perfil atualizado."
            st.rerun()

    # ---- ativar / desativar
    rotulo = "Desativar conta" if conta["ativo"] else "Ativar conta"

    if st.button(rotulo, disabled=eh_voce):
        try:
            autenticacao.definir_ativo(usuario, conta["id_usuario"], not conta["ativo"])
        except (ValueError, permissoes.PermissaoNegada) as erro:
            st.error(str(erro))
        else:
            st.session_state[CHAVE_AVISO] = "Situação da conta atualizada."
            st.rerun()

    # ---- redefinir senha
    with st.form("form_redefinir_senha", clear_on_submit=True):
        nova_senha = st.text_input(
            "Nova senha",
            type="password",
            help=f"Mínimo de {autenticacao.TAMANHO_MINIMO_SENHA} caracteres."
        )
        redefinir = st.form_submit_button("Redefinir senha")

    if redefinir:
        try:
            autenticacao.redefinir_senha(usuario, conta["id_usuario"], nova_senha)
        except (ValueError, permissoes.PermissaoNegada) as erro:
            st.error(str(erro))
        else:
            st.session_state[CHAVE_AVISO] = f"Senha de {conta['matricula']} redefinida."
            st.rerun()
