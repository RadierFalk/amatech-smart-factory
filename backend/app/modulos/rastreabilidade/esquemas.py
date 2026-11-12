"""Contratos de entrada e saída da API de Rastreabilidade (/api/ras)."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.core import tempo
from app.modulos.rastreabilidade.constantes import ESTOQUE_CRITICO, StatusSolicitacao
from app.modulos.rastreabilidade.modelos import (
    Baixa,
    Componente,
    Etapa,
    Modelo,
    NaoConformidade,
    Passagem,
    Producao,
    Solicitacao,
)

# ---------------------------------------------------------------- entrada


class EtapaEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=50)
    ordem: int | None = Field(None, ge=0, le=999, description="Vazio: vai para o fim do fluxo principal")


class ComponenteCriar(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    nome: str = Field(min_length=1, max_length=100)
    estoque: int = Field(0, ge=0)


class ComponenteAlterar(BaseModel):
    sku: str | None = Field(None, min_length=1, max_length=50)
    nome: str | None = Field(None, min_length=1, max_length=100)
    estoque: int | None = Field(None, ge=0)
    ativo: bool | None = None


class ItemLista(BaseModel):
    componente_id: int
    quantidade: int = Field(gt=0)


class ModeloCriar(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nome: str = Field(min_length=1, max_length=100)
    meta: int | None = Field(None, ge=0)
    componentes: list[ItemLista] = []

    def lista(self) -> list[tuple[int, int]]:
        return [(i.componente_id, i.quantidade) for i in self.componentes]


class ModeloAlterar(BaseModel):
    codigo: str | None = Field(None, min_length=1, max_length=50)
    nome: str | None = Field(None, min_length=1, max_length=100)
    meta: int | None = Field(None, ge=0)
    ativo: bool | None = None
    componentes: list[ItemLista] | None = None


class ProducaoCriar(BaseModel):
    modelo_id: int
    responsavel_id: int | None = None


class ProducaoAlterar(BaseModel):
    modelo_id: int
    responsavel_id: int | None = None


class AvancarEtapa(BaseModel):
    etapa_id: int
    responsavel_id: int | None = None
    descricao_falha: str | None = Field(None, max_length=2000)
    motivo_reprovacao: str | None = Field(None, max_length=2000)


class NaoConformidadeEntrada(BaseModel):
    descricao_falha: str = Field(min_length=1, max_length=2000)
    motivo_reprovacao: str = Field(min_length=1, max_length=2000)


class SolicitacaoCriar(BaseModel):
    producao_id: int
    componente_id: int
    quantidade: int = Field(gt=0)


class SolicitacaoAlterar(BaseModel):
    quantidade: int = Field(gt=0)
    cancelada: bool = False


class BaixaEntrada(BaseModel):
    quantidade: int = Field(gt=0)


class BaixaCriar(BaixaEntrada):
    solicitacao_id: int


class MaquinaStatus(BaseModel):
    numero_serie: str = Field(min_length=1, max_length=30)
    etapa: str = Field(min_length=1, max_length=50, description="Nome da etapa (ex.: Em Teste, Reprovado)")
    maquina: str | None = Field(None, max_length=50)


# ---------------------------------------------------------------- saída


class EtapaSaida(BaseModel):
    id: int
    nome: str
    ordem: int

    @classmethod
    def de(cls, e: Etapa) -> "EtapaSaida":
        return cls(id=e.id, nome=e.nome, ordem=e.ordem)


class ComponenteSaida(BaseModel):
    id: int
    sku: str
    nome: str
    estoque: int
    ativo: bool
    estoque_critico: bool
    pendente: int = Field(description="Solicitado e ainda não baixado")

    @classmethod
    def de(cls, c: Componente, pendente: int = 0) -> "ComponenteSaida":
        return cls(id=c.id, sku=c.sku, nome=c.nome, estoque=c.estoque, ativo=c.ativo,
                   estoque_critico=c.estoque <= ESTOQUE_CRITICO, pendente=pendente)


class ItemListaSaida(BaseModel):
    componente_id: int
    sku: str
    nome: str
    estoque: int
    quantidade: int


class ModeloSaida(BaseModel):
    id: int
    codigo: str
    nome: str
    meta: int | None
    ativo: bool
    producoes: int
    componentes: list[ItemListaSaida]

    @classmethod
    def de(cls, m: Modelo, producoes: int = 0) -> "ModeloSaida":
        itens = sorted(m.componentes, key=lambda i: i.componente.nome)
        return cls(id=m.id, codigo=m.codigo, nome=m.nome, meta=m.meta, ativo=m.ativo, producoes=producoes,
                   componentes=[ItemListaSaida(componente_id=i.componente_id, sku=i.componente.sku,
                                               nome=i.componente.nome, estoque=i.componente.estoque,
                                               quantidade=i.quantidade) for i in itens])


class ProducaoSaida(BaseModel):
    id: int
    numero_serie: str
    id_unica: str
    modelo_id: int
    modelo_nome: str
    modelo_codigo: str
    etapa_id: int
    etapa_nome: str
    etapa_ordem: int
    responsavel_id: int
    responsavel_nome: str
    criado_por_nome: str
    iniciada_em: datetime
    atualizada_em: datetime

    @classmethod
    def de(cls, p: Producao) -> "ProducaoSaida":
        return cls(
            id=p.id, numero_serie=p.numero_serie, id_unica=p.id_unica, modelo_id=p.modelo_id,
            modelo_nome=p.modelo.nome, modelo_codigo=p.modelo.codigo, etapa_id=p.etapa_id, etapa_nome=p.etapa.nome,
            etapa_ordem=p.etapa.ordem, responsavel_id=p.responsavel_id, responsavel_nome=p.responsavel.nome,
            criado_por_nome=p.criado_por.nome, iniciada_em=tempo.utc(p.iniciada_em), atualizada_em=tempo.utc(p.atualizada_em),
        )


class PassagemSaida(BaseModel):
    id: int
    etapa_nome: str
    usuario_nome: str
    responsavel_nome: str | None
    registrada_em: datetime
    origem: str

    @classmethod
    def de(cls, h: Passagem) -> "PassagemSaida":
        return cls(id=h.id, etapa_nome=h.etapa.nome, usuario_nome=h.usuario.nome,
                   responsavel_nome=h.responsavel.nome if h.responsavel else None,
                   registrada_em=tempo.utc(h.registrada_em), origem=h.origem)


class NaoConformidadeSaida(BaseModel):
    id: int
    descricao_falha: str
    motivo_reprovacao: str
    usuario_nome: str
    registrada_em: datetime
    origem_sistema: str | None
    id_externo: str | None

    @classmethod
    def de(cls, n: NaoConformidade) -> "NaoConformidadeSaida":
        return cls(id=n.id, descricao_falha=n.descricao_falha, motivo_reprovacao=n.motivo_reprovacao,
                   usuario_nome=n.usuario.nome, registrada_em=tempo.utc(n.registrada_em),
                   origem_sistema=n.origem_sistema, id_externo=n.id_externo)


class SolicitacaoSaida(BaseModel):
    id: int
    producao_id: int
    numero_serie: str
    componente_id: int
    componente_nome: str
    sku: str
    estoque: int
    quantidade: int
    quantidade_baixada: int
    status: StatusSolicitacao
    solicitante_nome: str
    criada_em: datetime

    @classmethod
    def de(cls, s: Solicitacao) -> "SolicitacaoSaida":
        return cls(id=s.id, producao_id=s.producao_id, numero_serie=s.producao.numero_serie,
                   componente_id=s.componente_id, componente_nome=s.componente.nome, sku=s.componente.sku,
                   estoque=s.componente.estoque, quantidade=s.quantidade, quantidade_baixada=s.quantidade_baixada,
                   status=s.status, solicitante_nome=s.criado_por.nome, criada_em=tempo.utc(s.criada_em))


class BaixaSaida(BaseModel):
    id: int
    solicitacao_id: int
    numero_serie: str
    componente_nome: str
    sku: str
    quantidade: int
    usuario_nome: str
    registrada_em: datetime

    @classmethod
    def de(cls, b: Baixa) -> "BaixaSaida":
        s = b.solicitacao
        return cls(id=b.id, solicitacao_id=b.solicitacao_id, numero_serie=s.producao.numero_serie,
                   componente_nome=s.componente.nome, sku=s.componente.sku, quantidade=b.quantidade,
                   usuario_nome=b.usuario.nome, registrada_em=tempo.utc(b.registrada_em))


class ProducaoDetalhe(ProducaoSaida):
    passagens: list[PassagemSaida]
    nao_conformidades: list[NaoConformidadeSaida]
    solicitacoes: list[SolicitacaoSaida]
    materiais_pendentes: int
    mesmo_modelo: list[ProducaoSaida]
    proxima_etapa_id: int | None


class PermissoesRas(BaseModel):
    producao: bool
    excluir_producao: bool
    solicitar: bool
    baixar: bool
    componentes: bool
    modelos_etapas: bool


class OpcoesSaida(BaseModel):
    etapas: list[EtapaSaida]
    responsaveis: list[dict]
    status_solicitacao: list[StatusSolicitacao]
    limite_estoque_critico: int
    permissoes: PermissoesRas
