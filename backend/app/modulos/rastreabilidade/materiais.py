"""Fluxo de materiais (portado de rastreabilidade/app/servicos/materiais.py).

Regras:
- RF014  Solicitação: PENDENTE (nada baixado) -> PARCIAL -> ATENDIDA; CANCELADA não muda mais de status.
- RF016  "Solicitar materiais" cria uma solicitação por componente da lista do modelo, sem repetir os que já têm
         solicitação ativa nessa produção.
- RF015  Baixa tira do estoque; não passa do saldo da solicitação nem do estoque. Alterar ou excluir a baixa
         devolve a diferença ao estoque. O componente é travado (FOR UPDATE) para duas baixas simultâneas não
         venderem o mesmo estoque.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import ErroNegocio, NaoEncontrado
from app.modulos.rastreabilidade.constantes import StatusSolicitacao
from app.modulos.rastreabilidade.modelos import Baixa, Componente, Producao, Solicitacao
from app.modulos.usuarios.modelos import Usuario

# ---------------------------------------------------------------- solicitações


def listar_solicitacoes(
    sessao: Session, status: StatusSolicitacao | None = None, producao_id: int | None = None, limite: int = 1000
) -> list[Solicitacao]:
    consulta = select(Solicitacao)
    if status:
        consulta = consulta.where(Solicitacao.status == status.value)
    if producao_id:
        consulta = consulta.where(Solicitacao.producao_id == producao_id)
    return list(sessao.scalars(consulta.order_by(Solicitacao.id.desc()).limit(limite)))


def obter_solicitacao(sessao: Session, solicitacao_id: int) -> Solicitacao:
    s = sessao.get(Solicitacao, solicitacao_id)
    if s is None:
        raise NaoEncontrado("Solicitação não encontrada.")
    return s


def _recalcular_status(sessao: Session, s: Solicitacao) -> None:
    if s.status == StatusSolicitacao.CANCELADA:
        return
    sessao.flush()
    sessao.refresh(s, ["baixas"])
    baixado = s.quantidade_baixada
    if baixado == 0:
        s.status = StatusSolicitacao.PENDENTE.value
    elif baixado >= s.quantidade:
        s.status = StatusSolicitacao.ATENDIDA.value
    else:
        s.status = StatusSolicitacao.PARCIAL.value


def criar_solicitacao(sessao: Session, executor: Usuario, *, producao_id: int, componente_id: int, quantidade: int) -> Solicitacao:
    if sessao.get(Producao, producao_id) is None:
        raise ErroNegocio("Produção não encontrada.", status=422)
    componente = sessao.get(Componente, componente_id)
    if componente is None or not componente.ativo:
        raise ErroNegocio("Componente não encontrado ou inativo.", status=422)
    s = Solicitacao(producao_id=producao_id, componente_id=componente_id, quantidade=quantidade,
                    status=StatusSolicitacao.PENDENTE.value, criado_por_id=executor.id, criada_em=tempo.agora())
    sessao.add(s)
    sessao.flush()
    sessao.refresh(s)
    return s


def solicitar_lista_do_modelo(sessao: Session, executor: Usuario, producao_id: int) -> dict[str, int]:
    producao = sessao.get(Producao, producao_id)
    if producao is None:
        raise NaoEncontrado("Produção não encontrada.")
    lista = producao.modelo.componentes
    if not lista:
        raise ErroNegocio("O modelo desta produção não tem componentes vinculados. "
                          "Vincule-os em Cadastros > Modelos.", status=409)
    ativos = set(sessao.scalars(select(Solicitacao.componente_id).where(
        Solicitacao.producao_id == producao_id, Solicitacao.status != StatusSolicitacao.CANCELADA.value
    )))
    criadas = 0
    agora = tempo.agora()
    for item in lista:
        if item.componente_id in ativos:
            continue
        sessao.add(Solicitacao(producao_id=producao_id, componente_id=item.componente_id, quantidade=item.quantidade,
                               status=StatusSolicitacao.PENDENTE.value, criado_por_id=executor.id, criada_em=agora))
        criadas += 1
    sessao.flush()
    return {"criadas": criadas, "ignoradas": len(lista) - criadas}


def alterar_solicitacao(sessao: Session, solicitacao_id: int, *, quantidade: int, cancelada: bool) -> Solicitacao:
    s = obter_solicitacao(sessao, solicitacao_id)
    if quantidade < s.quantidade_baixada:
        raise ErroNegocio(f"A quantidade não pode ser menor que a já baixada ({s.quantidade_baixada}).", status=409)
    s.quantidade = quantidade
    s.status = (StatusSolicitacao.CANCELADA if cancelada else StatusSolicitacao.PENDENTE).value
    _recalcular_status(sessao, s)
    sessao.flush()
    return s


def excluir_solicitacao(sessao: Session, solicitacao_id: int) -> None:
    s = obter_solicitacao(sessao, solicitacao_id)
    if s.baixas:
        raise ErroNegocio("Esta solicitação já tem baixas. Exclua as baixas primeiro (o estoque é devolvido) "
                          "ou cancele a solicitação.", status=409)
    sessao.delete(s)
    sessao.flush()


# ---------------------------------------------------------------- baixas


def listar_baixas(sessao: Session, limite: int = 1000) -> list[Baixa]:
    return list(sessao.scalars(select(Baixa).order_by(Baixa.id.desc()).limit(limite)))


def _travar_componente(sessao: Session, componente_id: int) -> Componente:
    return sessao.get(Componente, componente_id, with_for_update=True, populate_existing=True)


def _validar(s: Solicitacao, componente: Componente, nova: int, antiga: int = 0) -> None:
    saldo = s.quantidade - (s.quantidade_baixada - antiga)
    if nova > saldo:
        raise ErroNegocio(f"Quantidade maior que o saldo da solicitação ({saldo}).", status=409)
    disponivel = componente.estoque + antiga
    if nova > disponivel:
        raise ErroNegocio(f"Estoque insuficiente: disponível {disponivel}, solicitado {nova}.", status=409)


def criar_baixa(sessao: Session, executor: Usuario, *, solicitacao_id: int, quantidade: int) -> Baixa:
    s = obter_solicitacao(sessao, solicitacao_id)
    if s.status == StatusSolicitacao.CANCELADA:
        raise ErroNegocio("Não é possível dar baixa em solicitação cancelada.", status=409)
    componente = _travar_componente(sessao, s.componente_id)
    _validar(s, componente, quantidade)
    baixa = Baixa(solicitacao_id=s.id, usuario_id=executor.id, quantidade=quantidade, registrada_em=tempo.agora())
    sessao.add(baixa)
    componente.estoque -= quantidade
    _recalcular_status(sessao, s)
    sessao.flush()
    return baixa


def _obter_baixa(sessao: Session, baixa_id: int) -> Baixa:
    b = sessao.get(Baixa, baixa_id)
    if b is None:
        raise NaoEncontrado("Baixa não encontrada.")
    return b


def alterar_baixa(sessao: Session, baixa_id: int, *, quantidade: int) -> Baixa:
    baixa = _obter_baixa(sessao, baixa_id)
    s = baixa.solicitacao
    componente = _travar_componente(sessao, s.componente_id)
    _validar(s, componente, quantidade, baixa.quantidade)
    componente.estoque += baixa.quantidade - quantidade
    baixa.quantidade = quantidade
    _recalcular_status(sessao, s)
    sessao.flush()
    return baixa


def excluir_baixa(sessao: Session, baixa_id: int) -> None:
    baixa = _obter_baixa(sessao, baixa_id)
    s = baixa.solicitacao
    componente = _travar_componente(sessao, s.componente_id)
    componente.estoque += baixa.quantidade
    sessao.delete(baixa)
    _recalcular_status(sessao, s)
    sessao.flush()
