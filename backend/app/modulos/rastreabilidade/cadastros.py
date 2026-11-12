"""Cadastros da Rastreabilidade: etapas, componentes e modelos com a lista de componentes (BOM).

Componentes e modelos não são apagados, só inativados (produções e solicitações apontam para eles).
Etapa só é excluída se nunca foi usada.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.erros import ErroNegocio, NaoEncontrado
from app.modulos.rastreabilidade.constantes import ORDEM_LATERAL, SOLICITACAO_ABERTA
from app.modulos.rastreabilidade.modelos import (
    Componente,
    Etapa,
    Modelo,
    ModeloComponente,
    Passagem,
    Producao,
    Solicitacao,
)

# ---------------------------------------------------------------- etapas


def listar_etapas(sessao: Session) -> list[Etapa]:
    return list(sessao.scalars(select(Etapa).order_by(Etapa.ordem, Etapa.id)))


def etapa_por_nome(sessao: Session, nome: str) -> Etapa | None:
    return sessao.scalar(select(Etapa).where(func.lower(Etapa.nome) == nome.strip().lower()))


def _ordem_padrao(sessao: Session) -> int:
    maior = sessao.scalar(select(func.max(Etapa.ordem)).where(Etapa.ordem < ORDEM_LATERAL))
    return (maior or 0) + 1


def _exigir_nome_livre(sessao: Session, nome: str, exceto_id: int | None = None) -> None:
    existente = etapa_por_nome(sessao, nome)
    if existente and existente.id != exceto_id:
        raise ErroNegocio(f"Já existe a etapa '{existente.nome}'.", status=409)


def criar_etapa(sessao: Session, *, nome: str, ordem: int | None) -> Etapa:
    nome = nome.strip()
    _exigir_nome_livre(sessao, nome)
    etapa = Etapa(nome=nome, ordem=ordem if ordem is not None else _ordem_padrao(sessao))
    sessao.add(etapa)
    sessao.flush()
    return etapa


def alterar_etapa(sessao: Session, etapa_id: int, *, nome: str, ordem: int | None) -> Etapa:
    etapa = sessao.get(Etapa, etapa_id)
    if etapa is None:
        raise NaoEncontrado("Etapa não encontrada.")
    nome = nome.strip()
    _exigir_nome_livre(sessao, nome, exceto_id=etapa_id)
    etapa.nome = nome
    etapa.ordem = ordem if ordem is not None else _ordem_padrao(sessao)
    sessao.flush()
    return etapa


def excluir_etapa(sessao: Session, etapa_id: int) -> None:
    etapa = sessao.get(Etapa, etapa_id)
    if etapa is None:
        raise NaoEncontrado("Etapa não encontrada.")
    usada = sessao.scalar(select(Producao.id).where(Producao.etapa_id == etapa_id).limit(1)) or sessao.scalar(
        select(Passagem.id).where(Passagem.etapa_id == etapa_id).limit(1)
    )
    if usada:
        raise ErroNegocio("Esta etapa já foi usada em produções ou no histórico e não pode ser excluída.", status=409)
    sessao.delete(etapa)
    sessao.flush()


# ---------------------------------------------------------------- componentes


def pendente_por_componente(sessao: Session) -> dict[int, int]:
    """Quantidade solicitada e ainda não baixada (solicitações PENDENTE/PARCIAL), por componente."""
    pendente: dict[int, int] = {}
    for s in sessao.scalars(select(Solicitacao).where(Solicitacao.status.in_(SOLICITACAO_ABERTA))):
        pendente[s.componente_id] = pendente.get(s.componente_id, 0) + s.quantidade - s.quantidade_baixada
    return pendente


def listar_componentes(sessao: Session, incluir_inativos: bool = False) -> list[Componente]:
    consulta = select(Componente)
    if not incluir_inativos:
        consulta = consulta.where(Componente.ativo.is_(True))
    return list(sessao.scalars(consulta.order_by(Componente.nome)))


def _exigir_sku_livre(sessao: Session, sku: str, exceto_id: int | None = None) -> None:
    existente = sessao.scalar(select(Componente.id).where(Componente.sku == sku))
    if existente and existente != exceto_id:
        raise ErroNegocio(f"Já existe um componente com o SKU '{sku}'.", status=409)


def criar_componente(sessao: Session, *, sku: str, nome: str, estoque: int) -> Componente:
    sku = sku.strip().upper()
    _exigir_sku_livre(sessao, sku)
    c = Componente(sku=sku, nome=nome.strip(), estoque=estoque)
    sessao.add(c)
    sessao.flush()
    return c


def alterar_componente(sessao: Session, componente_id: int, **valores) -> Componente:
    c = sessao.get(Componente, componente_id)
    if c is None:
        raise NaoEncontrado("Componente não encontrado.")
    if "sku" in valores:
        valores["sku"] = valores["sku"].strip().upper()
        _exigir_sku_livre(sessao, valores["sku"], exceto_id=componente_id)
    if "nome" in valores:
        valores["nome"] = valores["nome"].strip()
    for chave, valor in valores.items():
        setattr(c, chave, valor)
    sessao.flush()
    return c


# ---------------------------------------------------------------- modelos (com a lista de componentes)


def listar_modelos(sessao: Session, incluir_inativos: bool = False) -> list[Modelo]:
    consulta = select(Modelo)
    if not incluir_inativos:
        consulta = consulta.where(Modelo.ativo.is_(True))
    return list(sessao.scalars(consulta.order_by(Modelo.nome)))


def obter_modelo(sessao: Session, modelo_id: int) -> Modelo:
    m = sessao.get(Modelo, modelo_id)
    if m is None:
        raise NaoEncontrado("Modelo não encontrado.")
    return m


def producoes_por_modelo(sessao: Session) -> dict[int, int]:
    return dict(sessao.execute(select(Producao.modelo_id, func.count()).group_by(Producao.modelo_id)).all())


def _sincronizar_lista(sessao: Session, modelo: Modelo, lista: list[tuple[int, int]]) -> None:
    """Deixa a lista de componentes do modelo igual à recebida: [(componente_id, quantidade)]."""
    novos: dict[int, int] = {}
    for componente_id, quantidade in lista:
        if componente_id in novos:
            raise ErroNegocio("O mesmo componente foi vinculado mais de uma vez ao modelo.", status=422)
        if sessao.get(Componente, componente_id) is None:
            raise ErroNegocio(f"Componente {componente_id} não existe.", status=422)
        novos[componente_id] = quantidade
    atuais = {item.componente_id: item for item in modelo.componentes}
    for componente_id, item in atuais.items():
        if componente_id not in novos:
            modelo.componentes.remove(item)
    for componente_id, quantidade in novos.items():
        if componente_id in atuais:
            atuais[componente_id].quantidade = quantidade
        else:
            modelo.componentes.append(ModeloComponente(componente_id=componente_id, quantidade=quantidade))


def _exigir_codigo_livre(sessao: Session, codigo: str, exceto_id: int | None = None) -> None:
    existente = sessao.scalar(select(Modelo.id).where(Modelo.codigo == codigo))
    if existente and existente != exceto_id:
        raise ErroNegocio(f"Já existe um modelo com o código '{codigo}'.", status=409)


def criar_modelo(sessao: Session, *, codigo: str, nome: str, meta: int | None, componentes: list[tuple[int, int]]) -> Modelo:
    codigo = codigo.strip().upper()
    _exigir_codigo_livre(sessao, codigo)
    modelo = Modelo(codigo=codigo, nome=nome.strip(), meta=meta)
    sessao.add(modelo)
    _sincronizar_lista(sessao, modelo, componentes)
    sessao.flush()
    return modelo


def alterar_modelo(sessao: Session, modelo_id: int, *, componentes: list[tuple[int, int]] | None = None, **valores) -> Modelo:
    modelo = obter_modelo(sessao, modelo_id)
    if "codigo" in valores:
        valores["codigo"] = valores["codigo"].strip().upper()
        _exigir_codigo_livre(sessao, valores["codigo"], exceto_id=modelo_id)
    if "nome" in valores:
        valores["nome"] = valores["nome"].strip()
    for chave, valor in valores.items():
        setattr(modelo, chave, valor)
    if componentes is not None:
        _sincronizar_lista(sessao, modelo, componentes)
    sessao.flush()
    return modelo
