"""
Sessão do usuário na tela (Streamlit).

O que fica em st.session_state é só o id do usuário e o horário do último acesso: nunca a senha nem o hash.
A cada interação o usuário é lido de novo no banco, então:
  - mudar o perfil de alguém ou desativar a conta vale na hora, sem esperar a sessão acabar;
  - a sessão expira por inatividade (QUALIDADE_SESSAO_MINUTOS, padrão 30);
  - ao sair, todo o estado da sessão é apagado.

Limite do Streamlit: a sessão vive na aba do navegador. Atualizar a página (F5) ou abrir outra aba pede
login de novo; as interações normais com a tela não pedem.
"""
import os
import time

import autenticacao


CHAVE = "_sessao_qualidade"
CHAVE_AVISO = "_aviso_login"

MINUTOS_DE_INATIVIDADE = float(os.environ.get("QUALIDADE_SESSAO_MINUTOS", "30"))


def _estado(estado):
    """O estado da sessão: o st.session_state, ou um dicionário (nos testes)."""
    if estado is not None:
        return estado

    import streamlit as st
    return st.session_state


def iniciar(usuario, estado=None, agora=None):
    estado = _estado(estado)
    estado[CHAVE] = {
        "id_usuario": usuario["id_usuario"],
        "ultimo_acesso": time.time() if agora is None else agora,
    }


def encerrar(estado=None, aviso=None):
    """Apaga tudo da sessão. `aviso` aparece na tela de login (ex.: sessão expirada)."""
    estado = _estado(estado)
    estado.clear()

    if aviso:
        estado[CHAVE_AVISO] = aviso


def usuario_atual(estado=None, agora=None):
    """Usuário autenticado e ativo, ou None (sem sessão, expirada ou conta que não pode mais entrar)."""
    estado = _estado(estado)
    dados = estado.get(CHAVE)

    if not dados:
        return None

    agora = time.time() if agora is None else agora

    if agora - dados["ultimo_acesso"] > MINUTOS_DE_INATIVIDADE * 60:
        encerrar(estado, aviso="Sua sessão expirou por inatividade. Entre novamente.")
        return None

    usuario = autenticacao.obter_usuario_ativo(dados["id_usuario"])

    if usuario is None:
        encerrar(estado, aviso="Esta conta não tem mais acesso ao sistema.")
        return None

    dados["ultimo_acesso"] = agora
    return usuario
