"""Rotas de autenticação (/api/auth) e gestão de usuários (/api/usuarios, só Administrador)."""
from fastapi import APIRouter, Depends, status

from app.core.deps import SessaoDep, UsuarioAtual, exigir_modulo
from app.core.rbac import Modulo, modulos_do_perfil
from app.core.seguranca import criar_token
from app.modulos.usuarios import servico
from app.modulos.usuarios.esquemas import (
    LoginEntrada,
    ModuloSaida,
    SenhaRedefinir,
    TokenSaida,
    UsuarioAlterar,
    UsuarioCriar,
    UsuarioSaida,
)
from app.modulos.usuarios.modelos import Usuario

rotas_auth = APIRouter(prefix="/api/auth", tags=["Autenticação"])
rotas_usuarios = APIRouter(
    prefix="/api/usuarios",
    tags=["Usuários (USR)"],
    dependencies=[Depends(exigir_modulo(Modulo.USUARIOS))],
)


@rotas_auth.post("/login", response_model=TokenSaida)
def login(entrada: LoginEntrada, sessao: SessaoDep):
    usuario = servico.autenticar(sessao, entrada.matricula, entrada.senha)
    token = criar_token(str(usuario.id), {"matricula": usuario.matricula, "perfil": usuario.perfil})
    return TokenSaida(access_token=token, usuario=UsuarioSaida.model_validate(usuario))


@rotas_auth.get("/me", response_model=UsuarioSaida)
def eu(usuario: UsuarioAtual):
    return usuario


@rotas_auth.get("/modulos", response_model=list[ModuloSaida])
def meus_modulos(usuario: UsuarioAtual):
    """Módulos que a persona pode acessar: o Angular monta o hub a partir disso."""
    return [
        ModuloSaida(id=m.id.value, sigla=m.sigla, nome=m.nome, descricao=m.descricao)
        for m in modulos_do_perfil(usuario.perfil)
    ]


@rotas_usuarios.get("", response_model=list[UsuarioSaida])
def listar(sessao: SessaoDep):
    return servico.listar(sessao)


@rotas_usuarios.post("", response_model=UsuarioSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: UsuarioCriar, sessao: SessaoDep):
    return servico.criar(sessao, dados)


@rotas_usuarios.patch("/{usuario_id}", response_model=UsuarioSaida)
def alterar(usuario_id: int, dados: UsuarioAlterar, sessao: SessaoDep, executor: UsuarioAtual):
    return servico.alterar(sessao, usuario_id, dados, executor)


@rotas_usuarios.post("/{usuario_id}/senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(usuario_id: int, dados: SenhaRedefinir, sessao: SessaoDep):
    servico.redefinir_senha(sessao, usuario_id, dados.nova_senha)


__all__ = ["rotas_auth", "rotas_usuarios", "Usuario"]
