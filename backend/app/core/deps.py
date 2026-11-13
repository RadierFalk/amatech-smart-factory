"""Dependências do FastAPI para autenticação e autorização."""
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import obter_sessao
from app.core.rbac import Modulo, Perfil, tem_acesso
from app.core.seguranca import decodificar_token
from app.modulos.auditoria.registro import definir_usuario
from app.modulos.usuarios.modelos import Usuario

_bearer = HTTPBearer(auto_error=False)

SessaoDep = Annotated[Session, Depends(obter_sessao)]


def usuario_atual(
    sessao: SessaoDep,
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Usuario:
    nao_autorizado = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.", headers={"WWW-Authenticate": "Bearer"}
    )
    if credenciais is None:
        raise nao_autorizado
    try:
        corpo = decodificar_token(credenciais.credentials)
        usuario_id = int(corpo["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise nao_autorizado from None

    usuario = sessao.get(Usuario, usuario_id)
    # Conta desativada depois do login perde o acesso na hora, mesmo com token válido.
    if usuario is None or not usuario.ativo:
        raise nao_autorizado
    # A mesma sessão serve a rota: o que ela gravar fica na auditoria em nome desta pessoa.
    definir_usuario(sessao, usuario)
    return usuario


UsuarioAtual = Annotated[Usuario, Depends(usuario_atual)]


def exigir_modulo(modulo: Modulo) -> Callable[[Usuario], Usuario]:
    """Use em `dependencies=[Depends(exigir_modulo(Modulo.X))]` no router de cada módulo."""

    def verificar(usuario: UsuarioAtual) -> Usuario:
        if not tem_acesso(usuario.perfil, modulo):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não tem acesso a este módulo.")
        return usuario

    return verificar


def exigir_perfis(*perfis: Perfil) -> Callable[[Usuario], Usuario]:
    """Restringe uma rota específica a algumas personas (ex.: só Técnico executa O.S.)."""
    permitidos = frozenset(perfis)

    def verificar(usuario: UsuarioAtual) -> Usuario:
        if Perfil(usuario.perfil) not in permitidos:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Seu perfil não pode executar esta ação.")
        return usuario

    return verificar
