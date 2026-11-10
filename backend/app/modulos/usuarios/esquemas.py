"""Contratos de entrada e saída da API de usuários e autenticação."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.rbac import Perfil

SENHA_MINIMA = 8


class LoginEntrada(BaseModel):
    matricula: str = Field(min_length=1, max_length=20)
    senha: str = Field(min_length=1)


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricula: str
    nome: str
    perfil: Perfil
    ativo: bool
    criado_em: datetime


class TokenSaida(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioSaida


class ModuloSaida(BaseModel):
    id: str
    sigla: str
    nome: str
    descricao: str


class UsuarioCriar(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    perfil: Perfil
    senha: str = Field(min_length=SENHA_MINIMA)
    matricula: str | None = Field(default=None, max_length=20, description="Gerada pelo perfil se omitida")


class UsuarioAlterar(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    perfil: Perfil | None = None
    ativo: bool | None = None


class SenhaRedefinir(BaseModel):
    nova_senha: str = Field(min_length=SENHA_MINIMA)
