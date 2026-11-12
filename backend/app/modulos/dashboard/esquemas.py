"""Contratos de entrada e saída da API do Dashboard (/api/dsh)."""
from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.core import tempo
from app.modulos.dashboard.constantes import NOMES_INDICADORES, Indicador
from app.modulos.dashboard.modelos import Limite, Meta, Perda, TipoPerda, Turno

# ---------------------------------------------------------------- entrada


class MetaEntrada(BaseModel):
    data: date
    turno_id: int
    modelo_id: int
    quantidade: int = Field(gt=0, le=1_000_000)


class PerdaEntrada(BaseModel):
    data: date
    turno_id: int
    estacao_id: int
    modelo_id: int
    tipo_perda_id: int
    quantidade: int = Field(gt=0, le=1_000_000)
    observacao: str | None = Field(None, max_length=500)


class ImportacaoEntrada(BaseModel):
    conteudo: str = Field(min_length=1, max_length=2_000_000, description="Texto do arquivo CSV (; ou ,)")


class TurnoEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=30)
    hora_inicio: time
    hora_fim: time


class TipoPerdaCriar(BaseModel):
    nome: str = Field(min_length=1, max_length=60)


class TipoPerdaAlterar(BaseModel):
    ativo: bool


class LimiteEntrada(BaseModel):
    limite_verde: float = Field(ge=0)
    limite_amarelo: float = Field(ge=0)


# ---------------------------------------------------------------- saída


class TurnoSaida(BaseModel):
    id: int
    nome: str
    hora_inicio: str
    hora_fim: str
    duracao_min: int

    @classmethod
    def de(cls, t: Turno) -> "TurnoSaida":
        return cls(id=t.id, nome=t.nome, hora_inicio=t.hora_inicio.strftime("%H:%M"),
                   hora_fim=t.hora_fim.strftime("%H:%M"), duracao_min=t.duracao_min)


class TipoPerdaSaida(BaseModel):
    id: int
    nome: str
    ativo: bool

    @classmethod
    def de(cls, t: TipoPerda) -> "TipoPerdaSaida":
        return cls(id=t.id, nome=t.nome, ativo=t.ativo)


class LimiteSaida(BaseModel):
    indicador: Indicador
    nome: str
    limite_verde: float
    limite_amarelo: float
    sentido: str

    @classmethod
    def de(cls, l: Limite) -> "LimiteSaida":
        i = Indicador(l.indicador)
        return cls(indicador=i, nome=NOMES_INDICADORES[i], limite_verde=l.limite_verde,
                   limite_amarelo=l.limite_amarelo, sentido=l.sentido)


class MetaSaida(BaseModel):
    id: int
    data: date
    turno_id: int
    turno_nome: str
    modelo_id: int
    modelo_nome: str
    quantidade: int
    registrado_por_nome: str

    @classmethod
    def de(cls, m: Meta) -> "MetaSaida":
        return cls(id=m.id, data=m.data, turno_id=m.turno_id, turno_nome=m.turno.nome, modelo_id=m.modelo_id,
                   modelo_nome=m.modelo.nome, quantidade=m.quantidade, registrado_por_nome=m.registrado_por.nome)


class PerdaSaida(BaseModel):
    id: int
    data: date
    turno_nome: str
    estacao_nome: str
    modelo_nome: str
    tipo_nome: str
    quantidade: int
    observacao: str | None
    origem: str
    registrado_por_nome: str
    registrado_em: datetime

    @classmethod
    def de(cls, p: Perda) -> "PerdaSaida":
        return cls(id=p.id, data=p.data, turno_nome=p.turno.nome, estacao_nome=p.estacao.nome, modelo_nome=p.modelo.nome,
                   tipo_nome=p.tipo.nome, quantidade=p.quantidade, observacao=p.observacao, origem=p.origem,
                   registrado_por_nome=p.registrado_por.nome, registrado_em=tempo.utc(p.registrado_em))


class ErroLinhaSaida(BaseModel):
    linha: int
    coluna: str
    mensagem: str


class ImportacaoSaida(BaseModel):
    linhas_lidas: int
    importadas: int
    erros: list[ErroLinhaSaida]


class PermissoesDsh(BaseModel):
    lancar: bool = Field(description="Metas, perdas e importação de planilhas")
    configurar: bool = Field(description="Turnos, tipos de perda e limites do semáforo")


class OpcoesSaida(BaseModel):
    turnos: list[TurnoSaida]
    modelos: list[dict]
    estacoes: list[dict]
    tipos_perda: list[TipoPerdaSaida]
    limites: list[LimiteSaida]
    hoje: date
    permissoes: PermissoesDsh
