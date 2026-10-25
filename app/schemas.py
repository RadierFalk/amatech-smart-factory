"""Modelos (Pydantic) dos dados que chegam nas requisições."""
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    matricula: str = Field(min_length=1)
    senha: str = Field(min_length=1)
    turno: str = "Turno 1"


class UsuarioIn(BaseModel):
    matricula: str = Field(min_length=1, max_length=20)
    nome: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=100)
    cargo: str
    ativo: int = 1
    senha: str | None = None


class StatusIn(BaseModel):
    nome_status: str = Field(min_length=1, max_length=50)
    ordem: int | None = None


class ComponenteIn(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    codigo_sku: str = Field(min_length=1, max_length=50)
    qtd_estoque: int = Field(default=0, ge=0)


class ProdutoComponenteIn(BaseModel):
    componente_id: int
    quantidade_necessaria: int = Field(gt=0)


class ProdutoIn(BaseModel):
    nome_modelo: str = Field(min_length=1, max_length=100)
    codigo_modelo: str = Field(min_length=1, max_length=50)
    quantidade: int | None = Field(default=None, ge=0)
    componentes: list[ProdutoComponenteIn] = []


class ProducaoIn(BaseModel):
    produto_id: int
    responsavel_etapa_id: int | None = None


class ProducaoEdicaoIn(BaseModel):
    produto_id: int
    responsavel_etapa_id: int | None = None


class AvancarIn(BaseModel):
    status_id: int
    responsavel_etapa_id: int | None = None
    descricao_falha: str | None = None
    motivo_reprovacao: str | None = None


class NaoConformidadeIn(BaseModel):
    descricao_falha: str = Field(min_length=1)
    motivo_reprovacao: str = Field(min_length=1)


class SolicitacaoIn(BaseModel):
    producao_id: int
    componente_id: int
    quantidade_solicitada: int = Field(gt=0)


class SolicitacaoEdicaoIn(BaseModel):
    quantidade_solicitada: int = Field(gt=0)
    cancelada: bool = False


class BaixaIn(BaseModel):
    solicitacao_id: int
    quantidade_baixada: int = Field(gt=0)


class BaixaEdicaoIn(BaseModel):
    quantidade_baixada: int = Field(gt=0)


class MaquinaStatusIn(BaseModel):
    numero_serie: str = Field(min_length=1)
    status: str = Field(min_length=1)
    maquina: str | None = None


# ---------------- integração (API /api/v1 e administração das chaves)
class StatusExternoIn(BaseModel):
    status: str = Field(min_length=1)
    maquina: str | None = None


class NaoConformidadeExternaIn(BaseModel):
    numero_serie: str = Field(min_length=1)
    descricao_falha: str = Field(min_length=1)
    motivo_reprovacao: str = Field(min_length=1)
    id_externo: str | None = None     # id do registro no sistema de origem (evita duplicar em reenvios)


class ClienteIntegracaoIn(BaseModel):
    nome: str = Field(min_length=1, max_length=50)


class ClienteAtivoIn(BaseModel):
    ativo: bool
