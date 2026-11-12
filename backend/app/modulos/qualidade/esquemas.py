"""Contratos de entrada e saída da API de Qualidade (/api/qld)."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.core import tempo
from app.modulos.manutencao.constantes import StatusChamado, StatusEquipamento
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.constantes import Classificacao, SituacaoProduto, StatusOcorrencia
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.qualidade.servico import Aviso, DadosOcorrencia

# ---------------------------------------------------------------- entrada


class OcorrenciaEntrada(BaseModel):
    ocorrida_em: datetime = Field(description="Sem fuso, vale a hora da fábrica (Manaus)")
    classificacao: Classificacao
    situacao_produto: SituacaoProduto
    status: StatusOcorrencia = StatusOcorrencia.ABERTA
    observacao: str = Field(min_length=1, max_length=2000)
    acao_realizada: str = Field(min_length=1, max_length=2000)
    produto_id: int
    estacao_id: int
    tipo_defeito_id: int
    equipamento_id: int

    def dados(self) -> DadosOcorrencia:
        return DadosOcorrencia(**self.model_dump(include=set(DadosOcorrencia.__dataclass_fields__)))


class OcorrenciaRegistrar(OcorrenciaEntrada):
    abrir_chamado: bool = Field(False, description="Defeito causado pela máquina: abre chamado na Manutenção")


class ProdutoCriar(BaseModel):
    numero_serie: str = Field(min_length=1, max_length=30)
    modelo: str = Field(min_length=1, max_length=50)


class ProdutoAlterar(BaseModel):
    modelo: str | None = Field(None, min_length=1, max_length=50)
    ativo: bool | None = None


class ItemCriar(BaseModel):
    """Estação ou tipo de defeito."""

    nome: str = Field(min_length=1, max_length=60)
    descricao: str | None = Field(None, max_length=200)


class ItemAlterar(BaseModel):
    nome: str | None = Field(None, min_length=1, max_length=60)
    descricao: str | None = Field(None, max_length=200)
    ativo: bool | None = None


# ---------------------------------------------------------------- saída


class ProdutoSaida(BaseModel):
    id: int
    numero_serie: str
    modelo: str
    ativo: bool

    @classmethod
    def de(cls, p: Produto) -> "ProdutoSaida":
        return cls(id=p.id, numero_serie=p.numero_serie, modelo=p.modelo, ativo=p.ativo)


class ItemSaida(BaseModel):
    id: int
    nome: str
    descricao: str | None
    ativo: bool

    @classmethod
    def de(cls, i: Estacao | TipoDefeito) -> "ItemSaida":
        return cls(id=i.id, nome=i.nome, descricao=i.descricao, ativo=i.ativo)


class MaquinaSaida(BaseModel):
    id: int
    codigo_tag: str
    nome: str
    setor: str
    status_operacional: StatusEquipamento

    @classmethod
    def de(cls, e: Equipamento) -> "MaquinaSaida":
        return cls(id=e.id, codigo_tag=e.codigo_tag, nome=e.nome, setor=e.setor, status_operacional=e.status_operacional)


class OcorrenciaSaida(BaseModel):
    id: int
    ocorrida_em: datetime
    classificacao: Classificacao
    situacao_produto: SituacaoProduto
    status: StatusOcorrencia
    observacao: str
    acao_realizada: str
    produto_id: int
    numero_serie: str
    modelo: str
    estacao_id: int
    estacao_nome: str
    tipo_defeito_id: int
    tipo_defeito_nome: str
    equipamento_id: int
    equipamento_tag: str
    equipamento_nome: str
    responsavel_id: int
    responsavel_nome: str
    chamado_id: int | None = Field(description="Chamado aberto na Manutenção para esta ocorrência")
    chamado_status: StatusChamado | None

    @classmethod
    def de(cls, o: Ocorrencia, chamado: Chamado | None = None) -> "OcorrenciaSaida":
        return cls(
            id=o.id,
            ocorrida_em=tempo.utc(o.ocorrida_em),
            classificacao=o.classificacao,
            situacao_produto=o.situacao_produto,
            status=o.status,
            observacao=o.observacao,
            acao_realizada=o.acao_realizada,
            produto_id=o.produto_id,
            numero_serie=o.produto.numero_serie,
            modelo=o.produto.modelo,
            estacao_id=o.estacao_id,
            estacao_nome=o.estacao.nome,
            tipo_defeito_id=o.tipo_defeito_id,
            tipo_defeito_nome=o.tipo_defeito.nome,
            equipamento_id=o.equipamento_id,
            equipamento_tag=o.equipamento.codigo_tag,
            equipamento_nome=o.equipamento.nome,
            responsavel_id=o.responsavel_id,
            responsavel_nome=o.responsavel.nome,
            chamado_id=chamado.id if chamado else None,
            chamado_status=chamado.status_chamado if chamado else None,
        )


class AvisoSaida(BaseModel):
    tipo: str
    mensagem: str

    @classmethod
    def de(cls, a: Aviso) -> "AvisoSaida":
        return cls(tipo=a.tipo, mensagem=a.mensagem)


class RegistroSaida(BaseModel):
    ocorrencia: OcorrenciaSaida
    avisos: list[AvisoSaida]


class PermissoesQld(BaseModel):
    registrar: bool
    editar: bool
    ocultar: bool
    abrir_chamado: bool
    cadastros: bool


class OpcoesSaida(BaseModel):
    classificacoes: dict[str, str]
    situacoes: dict[str, str]
    status: dict[str, str]
    permissoes: PermissoesQld
