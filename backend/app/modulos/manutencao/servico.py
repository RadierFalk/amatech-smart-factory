"""Ciclo de vida do chamado / Ordem de Serviço (portado de manutencao/services/chamado_service.py).

Regras de negócio:
- RN02  Uma OS ativa por máquina; máquina PARADA ou EM_MANUTENCAO não recebe chamado novo.
        Também garantida por índice único parcial (ux_chamados_uma_os_ativa).
- RN03  Só o técnico responsável mexe na OS (laudo, peças, conclusão). A gestão (Supervisor/Administrador)
        pode concluir qualquer uma: isso é decidido na rota e chega aqui como `gestao=True`.
- RN04  Concluir exige diagnóstico, causa raiz e tipo de manutenção.
- RN05  Downtime = minutos da abertura até o fim do atendimento (mínimo 1).
- RN06  Datas e horas são do servidor, em UTC.
- RN08  Toda mudança de status de máquina vai para historico_status.
- RN09  Quantidade de peça > 0.

Quem pode chamar cada função (persona) é decidido nas rotas; aqui ficam as regras de negócio.
"""
from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import ErroNegocio, NaoEncontrado
from app.modulos.manutencao.constantes import (
    DESCRICAO_MINIMA,
    ORDEM_PRIORIDADE,
    STATUS_ATIVOS,
    Prioridade,
    StatusChamado,
    StatusEquipamento,
    TipoManutencao,
)
from app.modulos.manutencao.modelos import Chamado, ChamadoPeca, Equipamento, HistoricoStatus, Peca
from app.modulos.usuarios.modelos import Usuario


def _registrar_status(
    sessao: Session, equip: Equipamento, novo: StatusEquipamento, usuario: Usuario, chamado: Chamado | None, quando: datetime
) -> None:
    """Muda o status da máquina e grava a auditoria (RN08). Sem mudança real, não grava nada."""
    anterior = equip.status_operacional
    if anterior == novo.value:
        return
    equip.status_operacional = novo.value
    sessao.add(
        HistoricoStatus(
            equipamento_id=equip.id,
            chamado_id=chamado.id if chamado else None,
            usuario_id=usuario.id,
            status_anterior=anterior,
            status_novo=novo.value,
            alterado_em=quando,
        )
    )


def _os_ativa(sessao: Session, equipamento_id: int) -> Chamado | None:
    return sessao.scalar(
        select(Chamado)
        .where(Chamado.equipamento_id == equipamento_id, Chamado.status_chamado.in_(STATUS_ATIVOS))
        .order_by(Chamado.id.desc())
        .limit(1)
    )


def _travar_chamado(sessao: Session, chamado_id: int) -> Chamado:
    chamado = sessao.get(Chamado, chamado_id, with_for_update={"of": Chamado})
    if chamado is None:
        raise NaoEncontrado(f"Ordem de Serviço #{chamado_id} não encontrada.")
    return chamado


def _exigir_status(chamado: Chamado, *permitidos: StatusChamado, acao: str) -> None:
    if chamado.status_chamado not in permitidos:
        raise ErroNegocio(
            f"A OS #{chamado.id} não pode {acao}: status atual {chamado.status_chamado}.", status=409
        )


def _exigir_responsavel(chamado: Chamado, executor: Usuario, gestao: bool) -> None:
    if gestao:
        return
    if chamado.tecnico_responsavel_id != executor.id:
        raise ErroNegocio(
            "Regra RN03: apenas o técnico responsável pela OS (ou a gestão) pode alterá-la.", status=403
        )


# ---------------------------------------------------------------- abertura


def abrir_chamado(
    sessao: Session,
    *,
    equipamento_id: int,
    executor: Usuario,
    prioridade: Prioridade,
    descricao_falha: str,
    tipo_manutencao: TipoManutencao = TipoManutencao.CORRETIVA,
    parar_maquina: bool = True,
    origem_sistema: str | None = None,
    id_externo: str | None = None,
) -> Chamado:
    """Abre um chamado. Corretiva para a máquina (PARADA); preventiva programada não para (`parar_maquina=False`)."""
    descricao = (descricao_falha or "").strip()
    if len(descricao) < DESCRICAO_MINIMA:
        raise ErroNegocio(
            f"Descreva o sintoma ou a falha observada (mínimo de {DESCRICAO_MINIMA} caracteres).", status=422
        )

    # Trava a linha da máquina: duas aberturas simultâneas esperam uma pela outra.
    equip = sessao.get(Equipamento, equipamento_id, with_for_update=True)
    if equip is None:
        raise NaoEncontrado("Equipamento não encontrado.")
    if not equip.ativo:
        raise ErroNegocio(f"O equipamento {equip.codigo_tag} está inativo.", status=409)

    ativa = _os_ativa(sessao, equip.id)
    if equip.status_operacional != StatusEquipamento.OPERACIONAL or ativa is not None:
        vinculo = f"OS #{ativa.id}" if ativa else "uma OS ativa"
        raise ErroNegocio(
            f"Bloqueio de Redundância (RN02): a máquina {equip.codigo_tag} ({equip.nome}) já está "
            f"{equip.status_operacional} e vinculada a {vinculo}.",
            status=409,
        )

    quando = tempo.agora()
    chamado = Chamado(
        equipamento=equip,
        operador=executor,
        prioridade=prioridade.value,
        tipo_manutencao=tipo_manutencao.value,
        status_chamado=StatusChamado.ABERTO.value,
        descricao_falha=descricao,
        data_hora_abertura=quando,
        origem_sistema=(origem_sistema or "").strip().lower() or None,
        id_externo=(id_externo or "").strip() or None,
    )
    sessao.add(chamado)
    try:
        sessao.flush()
    except IntegrityError as exc:
        # Corrida que escapou da trava (ou reenvio externo duplicado): o índice único do banco segurou.
        raise ErroNegocio(
            f"Bloqueio de Redundância (RN02): a máquina {equip.codigo_tag} já tem uma OS ativa.", status=409
        ) from exc

    if parar_maquina:
        _registrar_status(sessao, equip, StatusEquipamento.PARADA, executor, chamado, quando)
    sessao.flush()
    return chamado


def abrir_chamado_por_tag(
    sessao: Session,
    *,
    equipamento_tag: str,
    executor: Usuario,
    descricao_falha: str,
    prioridade: Prioridade = Prioridade.MEDIA,
    tipo_manutencao: TipoManutencao = TipoManutencao.CORRETIVA,
    origem_sistema: str,
    id_externo: str | None = None,
) -> tuple[Chamado, bool]:
    """Abertura pedida por outro módulo (ex.: Qualidade achou defeito causado pela máquina).

    Devolve (chamado, criado). Um reenvio com o mesmo (origem_sistema, id_externo) devolve o chamado
    já existente, sem duplicar. As regras são as mesmas da abertura pela tela (RN02 incluída).
    """
    origem = origem_sistema.strip().lower()
    if id_externo:
        existente = sessao.scalar(
            select(Chamado).where(Chamado.origem_sistema == origem, Chamado.id_externo == id_externo.strip())
        )
        if existente:
            return existente, False
    tag = (equipamento_tag or "").strip().upper()
    equip = sessao.scalar(select(Equipamento).where(Equipamento.codigo_tag == tag))
    if equip is None:
        raise NaoEncontrado(f"Máquina com a TAG '{tag}' não encontrada.")
    chamado = abrir_chamado(
        sessao,
        equipamento_id=equip.id,
        executor=executor,
        prioridade=prioridade,
        descricao_falha=descricao_falha,
        tipo_manutencao=tipo_manutencao,
        origem_sistema=origem,
        id_externo=id_externo,
    )
    return chamado, True


# ---------------------------------------------------------------- atendimento


def assumir_chamado(sessao: Session, chamado_id: int, executor: Usuario) -> Chamado:
    """Técnico assume a OS: chamado EM_ANDAMENTO, máquina EM_MANUTENCAO."""
    chamado = _travar_chamado(sessao, chamado_id)
    _exigir_status(chamado, StatusChamado.ABERTO, acao="ser assumida")
    quando = tempo.agora()
    chamado.tecnico = executor
    chamado.status_chamado = StatusChamado.EM_ANDAMENTO.value
    chamado.data_hora_inicio_atendimento = quando
    _registrar_status(sessao, chamado.equipamento, StatusEquipamento.EM_MANUTENCAO, executor, chamado, quando)
    sessao.flush()
    return chamado


def salvar_laudo(
    sessao: Session,
    chamado_id: int,
    executor: Usuario,
    *,
    gestao: bool,
    diagnostico_tecnico: str,
    causa_raiz: str,
    tipo_manutencao: TipoManutencao,
) -> Chamado:
    """Rascunho do laudo durante o atendimento (pode ficar incompleto até a conclusão)."""
    chamado = _travar_chamado(sessao, chamado_id)
    _exigir_status(chamado, StatusChamado.EM_ANDAMENTO, acao="ter o laudo alterado")
    _exigir_responsavel(chamado, executor, gestao)
    chamado.diagnostico_tecnico = (diagnostico_tecnico or "").strip() or None
    chamado.causa_raiz = (causa_raiz or "").strip() or None
    chamado.tipo_manutencao = tipo_manutencao.value
    sessao.flush()
    return chamado


def adicionar_peca(
    sessao: Session, chamado_id: int, executor: Usuario, *, gestao: bool, peca_id: int, quantidade: Decimal
) -> Chamado:
    """Registra peça trocada (RN09). A mesma peça de novo soma a quantidade."""
    qtd = Decimal(quantidade).quantize(Decimal("0.01"))
    if qtd <= 0:
        raise ErroNegocio("Regra RN09: a quantidade de peças deve ser maior que zero.", status=422)
    chamado = _travar_chamado(sessao, chamado_id)
    _exigir_status(chamado, StatusChamado.EM_ANDAMENTO, acao="receber peças")
    _exigir_responsavel(chamado, executor, gestao)
    peca = sessao.get(Peca, peca_id)
    if peca is None or not peca.ativo:
        raise ErroNegocio("Peça inválida ou inativa no catálogo.", status=422)

    item = next((i for i in chamado.pecas if i.peca_id == peca_id), None)
    if item:
        item.quantidade = item.quantidade + qtd
    else:
        chamado.pecas.append(ChamadoPeca(peca_id=peca_id, quantidade=qtd))
    sessao.flush()
    return chamado


def remover_peca(sessao: Session, chamado_id: int, item_id: int, executor: Usuario, *, gestao: bool) -> Chamado:
    chamado = _travar_chamado(sessao, chamado_id)
    _exigir_status(chamado, StatusChamado.EM_ANDAMENTO, acao="ter peças removidas")
    _exigir_responsavel(chamado, executor, gestao)
    item = next((i for i in chamado.pecas if i.id == item_id), None)
    if item is None:
        raise NaoEncontrado("Peça não encontrada nesta OS.")
    chamado.pecas.remove(item)
    sessao.flush()
    return chamado


def concluir_chamado(
    sessao: Session,
    chamado_id: int,
    executor: Usuario,
    *,
    gestao: bool,
    diagnostico_tecnico: str,
    causa_raiz: str,
    tipo_manutencao: TipoManutencao,
) -> Chamado:
    """Conclui a OS: laudo obrigatório (RN04), downtime calculado (RN05), máquina OPERACIONAL."""
    diagnostico = (diagnostico_tecnico or "").strip()
    causa = (causa_raiz or "").strip()
    if not diagnostico:
        raise ErroNegocio("Regra RN04: o diagnóstico técnico é obrigatório para concluir a OS.", status=422)
    if not causa:
        raise ErroNegocio("Regra RN04: a causa raiz é obrigatória para concluir a OS.", status=422)

    chamado = _travar_chamado(sessao, chamado_id)
    _exigir_status(chamado, StatusChamado.EM_ANDAMENTO, acao="ser concluída")
    _exigir_responsavel(chamado, executor, gestao)

    quando = tempo.agora()
    chamado.status_chamado = StatusChamado.CONCLUIDO.value
    chamado.diagnostico_tecnico = diagnostico
    chamado.causa_raiz = causa
    chamado.tipo_manutencao = tipo_manutencao.value
    chamado.data_hora_fim_atendimento = quando
    chamado.downtime_minutos = tempo.minutos_entre(chamado.data_hora_abertura, quando)
    _registrar_status(sessao, chamado.equipamento, StatusEquipamento.OPERACIONAL, executor, chamado, quando)
    sessao.flush()
    return chamado


def cancelar_chamado(sessao: Session, chamado_id: int, executor: Usuario, *, motivo: str) -> Chamado:
    """Cancela uma OS aberta ou em andamento (alarme falso, duplicidade...). Máquina volta a OPERACIONAL."""
    motivo_limpo = (motivo or "").strip()
    if len(motivo_limpo) < DESCRICAO_MINIMA:
        raise ErroNegocio(f"Informe o motivo do cancelamento (mínimo de {DESCRICAO_MINIMA} caracteres).", status=422)
    chamado = _travar_chamado(sessao, chamado_id)
    _exigir_status(chamado, *STATUS_ATIVOS, acao="ser cancelada")
    quando = tempo.agora()
    chamado.status_chamado = StatusChamado.CANCELADO.value
    chamado.motivo_cancelamento = motivo_limpo
    chamado.data_hora_fim_atendimento = quando
    chamado.downtime_minutos = 0
    _registrar_status(sessao, chamado.equipamento, StatusEquipamento.OPERACIONAL, executor, chamado, quando)
    sessao.flush()
    return chamado


# ---------------------------------------------------------------- consultas


def obter_chamado(sessao: Session, chamado_id: int) -> Chamado:
    chamado = sessao.get(Chamado, chamado_id)
    if chamado is None:
        raise NaoEncontrado(f"Ordem de Serviço #{chamado_id} não encontrada.")
    return chamado


def listar_fila(sessao: Session, setor: str | None = None) -> list[Chamado]:
    """Chamados ABERTOS: Crítica primeiro e, na mesma prioridade, quem espera há mais tempo."""
    consulta = select(Chamado).join(Chamado.equipamento).where(Chamado.status_chamado == StatusChamado.ABERTO)
    if setor:
        consulta = consulta.where(Equipamento.setor == setor)
    chamados = list(sessao.scalars(consulta))
    return sorted(chamados, key=lambda c: (ORDEM_PRIORIDADE[Prioridade(c.prioridade)], tempo.utc(c.data_hora_abertura)))


def listar_chamados(
    sessao: Session,
    *,
    status: Sequence[StatusChamado] | None = None,
    tipo: TipoManutencao | None = None,
    prioridade: Prioridade | None = None,
    setor: str | None = None,
    equipamento_id: int | None = None,
    tecnico_id: int | None = None,
    operador_id: int | None = None,
    de: date | None = None,
    ate: date | None = None,
    busca: str | None = None,
    limite: int = 500,
) -> list[Chamado]:
    """Histórico com filtros (datas no dia da fábrica, UTC-4). Mais recentes primeiro."""
    consulta = select(Chamado).join(Chamado.equipamento)
    if status:
        consulta = consulta.where(Chamado.status_chamado.in_([s.value for s in status]))
    if tipo:
        consulta = consulta.where(Chamado.tipo_manutencao == tipo.value)
    if prioridade:
        consulta = consulta.where(Chamado.prioridade == prioridade.value)
    if setor:
        consulta = consulta.where(Equipamento.setor == setor)
    if equipamento_id:
        consulta = consulta.where(Chamado.equipamento_id == equipamento_id)
    if tecnico_id:
        consulta = consulta.where(Chamado.tecnico_responsavel_id == tecnico_id)
    if operador_id:
        consulta = consulta.where(Chamado.operador_abertura_id == operador_id)
    if de:
        consulta = consulta.where(Chamado.data_hora_abertura >= datetime.combine(de, time.min, tempo.FUSO_FABRICA))
    if ate:
        limite_sup = datetime.combine(ate + timedelta(days=1), time.min, tempo.FUSO_FABRICA)
        consulta = consulta.where(Chamado.data_hora_abertura < limite_sup)
    if busca and busca.strip():
        termo = f"%{busca.strip()}%"
        consulta = consulta.where(
            or_(
                Equipamento.codigo_tag.ilike(termo),
                Equipamento.nome.ilike(termo),
                Chamado.descricao_falha.ilike(termo),
                Chamado.diagnostico_tecnico.ilike(termo),
                Chamado.causa_raiz.ilike(termo),
            )
        )
    consulta = consulta.order_by(Chamado.data_hora_abertura.desc(), Chamado.id.desc()).limit(limite)
    return list(sessao.scalars(consulta).unique())


def listar_auditoria(sessao: Session, equipamento_id: int | None = None, limite: int = 100) -> list[HistoricoStatus]:
    consulta = select(HistoricoStatus)
    if equipamento_id:
        consulta = consulta.where(HistoricoStatus.equipamento_id == equipamento_id)
    consulta = consulta.order_by(HistoricoStatus.alterado_em.desc(), HistoricoStatus.id.desc()).limit(limite)
    return list(sessao.scalars(consulta))
