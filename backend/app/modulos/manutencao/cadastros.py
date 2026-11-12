"""Cadastro de máquinas (TAGs) e do catálogo de peças (portado de equipamento_service.py).

Nada é apagado: máquinas e peças são inativadas (RN07), porque o histórico de OS aponta para elas.
"""
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import ErroNegocio, NaoEncontrado
from app.modulos.manutencao.constantes import STATUS_ATIVOS, StatusEquipamento
from app.modulos.manutencao.modelos import Chamado, Equipamento, Peca

_ORDEM_STATUS = case(
    (Equipamento.status_operacional == StatusEquipamento.PARADA.value, 1),
    (Equipamento.status_operacional == StatusEquipamento.EM_MANUTENCAO.value, 2),
    else_=3,
)


def listar_equipamentos(
    sessao: Session, setor: str | None = None, incluir_inativos: bool = False
) -> list[tuple[Equipamento, Chamado | None]]:
    """Máquinas com a OS ativa de cada uma (painel). Paradas primeiro, depois em manutenção."""
    consulta = select(Equipamento)
    if not incluir_inativos:
        consulta = consulta.where(Equipamento.ativo.is_(True))
    if setor:
        consulta = consulta.where(Equipamento.setor == setor)
    equipamentos = list(sessao.scalars(consulta.order_by(_ORDEM_STATUS, Equipamento.codigo_tag)))

    # Uma consulta só para as OS ativas de todas as máquinas (evita N+1).
    ids = [e.id for e in equipamentos]
    ativas: dict[int, Chamado] = {}
    if ids:
        for c in sessao.scalars(
            select(Chamado)
            .where(Chamado.equipamento_id.in_(ids), Chamado.status_chamado.in_(STATUS_ATIVOS))
            .order_by(Chamado.id)
        ):
            ativas[c.equipamento_id] = c
    return [(e, ativas.get(e.id)) for e in equipamentos]


def listar_setores(sessao: Session) -> list[str]:
    return list(
        sessao.scalars(select(Equipamento.setor).where(Equipamento.ativo.is_(True)).distinct().order_by(Equipamento.setor))
    )


def obter_equipamento(sessao: Session, equipamento_id: int) -> Equipamento:
    equip = sessao.get(Equipamento, equipamento_id)
    if equip is None:
        raise NaoEncontrado("Equipamento não encontrado.")
    return equip


def criar_equipamento(sessao: Session, *, codigo_tag: str, nome: str, setor: str, posto_trabalho: str | None) -> Equipamento:
    tag = codigo_tag.strip().upper()
    if sessao.scalar(select(Equipamento.id).where(Equipamento.codigo_tag == tag)):
        raise ErroNegocio(f"Já existe uma máquina cadastrada com a TAG '{tag}'.", status=409)
    equip = Equipamento(
        codigo_tag=tag,
        nome=nome.strip(),
        setor=setor.strip(),
        posto_trabalho=(posto_trabalho or "").strip() or None,
        status_operacional=StatusEquipamento.OPERACIONAL.value,
        ativo=True,
    )
    sessao.add(equip)
    try:
        sessao.flush()
    except IntegrityError as exc:
        raise ErroNegocio(f"Já existe uma máquina cadastrada com a TAG '{tag}'.", status=409) from exc
    return equip


def alterar_equipamento(
    sessao: Session,
    equipamento_id: int,
    *,
    nome: str | None = None,
    setor: str | None = None,
    posto_trabalho: str | None = None,
    ativo: bool | None = None,
) -> Equipamento:
    equip = obter_equipamento(sessao, equipamento_id)
    if ativo is False and equip.ativo:
        ativa = sessao.scalar(
            select(Chamado.id).where(Chamado.equipamento_id == equip.id, Chamado.status_chamado.in_(STATUS_ATIVOS))
        )
        if ativa:
            raise ErroNegocio(
                f"Não é possível inativar {equip.codigo_tag}: a OS #{ativa} está aberta ou em andamento.", status=409
            )
    if nome is not None:
        equip.nome = nome.strip()
    if setor is not None:
        equip.setor = setor.strip()
    if posto_trabalho is not None:
        equip.posto_trabalho = posto_trabalho.strip() or None
    if ativo is not None:
        equip.ativo = ativo
    sessao.flush()
    return equip


def listar_pecas(sessao: Session, incluir_inativas: bool = False) -> list[Peca]:
    consulta = select(Peca)
    if not incluir_inativas:
        consulta = consulta.where(Peca.ativo.is_(True))
    return list(sessao.scalars(consulta.order_by(Peca.codigo_peca)))


def criar_peca(sessao: Session, *, codigo_peca: str, nome: str, unidade_medida: str) -> Peca:
    codigo = codigo_peca.strip().upper()
    if sessao.scalar(select(Peca.id).where(Peca.codigo_peca == codigo)):
        raise ErroNegocio(f"Já existe uma peça cadastrada com o código '{codigo}'.", status=409)
    peca = Peca(codigo_peca=codigo, nome=nome.strip(), unidade_medida=(unidade_medida or "UN").strip().upper(), ativo=True)
    sessao.add(peca)
    try:
        sessao.flush()
    except IntegrityError as exc:
        raise ErroNegocio(f"Já existe uma peça cadastrada com o código '{codigo}'.", status=409) from exc
    return peca


def alterar_peca(
    sessao: Session, peca_id: int, *, nome: str | None = None, unidade_medida: str | None = None, ativo: bool | None = None
) -> Peca:
    peca = sessao.get(Peca, peca_id)
    if peca is None:
        raise NaoEncontrado("Peça não encontrada.")
    if nome is not None:
        peca.nome = nome.strip()
    if unidade_medida is not None:
        peca.unidade_medida = unidade_medida.strip().upper()
    if ativo is not None:
        peca.ativo = ativo
    sessao.flush()
    return peca
