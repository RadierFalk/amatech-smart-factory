"""Produção e rastreabilidade (portado de rastreabilidade/app/servicos/producao.py).

Regras:
- RF002/004/005  Criar produção gera o número de série (AMT-000245) e o ID único (PRD-AMT-000245-AAAAMMDD,
                 dia da fábrica) e grava a primeira passagem, na primeira etapa do fluxo.
- RF006/008      Mudar de etapa grava quem mudou, quando, o novo responsável e a origem (manual, máquina, qualidade).
- RF011          Reprovar exige a falha e o motivo, e gera uma não conformidade.
- RF017          Máquinas informam a etapa pelo número de série; a mesma etapa de novo não grava nada.
- Uma reprovação vinda de outro módulo com o mesmo id_externo não é aplicada duas vezes.
Quem pode chamar cada função (persona) é decidido nas rotas.
"""
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import ErroNegocio, NaoEncontrado
from app.modulos.rastreabilidade.cadastros import etapa_por_nome, listar_etapas
from app.modulos.rastreabilidade.constantes import (
    ETAPA_APROVADO,
    ETAPA_MONTAGEM,
    ETAPA_REPROVADO,
    ORDEM_LATERAL,
    PREFIXO_SERIE,
    Origem,
)
from app.modulos.rastreabilidade.modelos import (
    Baixa,
    Etapa,
    Modelo,
    NaoConformidade,
    Passagem,
    Producao,
    Solicitacao,
)
from app.modulos.usuarios.modelos import Usuario

# ---------------------------------------------------------------- consultas


def listar(
    sessao: Session,
    *,
    busca: str | None = None,
    etapa_id: int | None = None,
    modelo_id: int | None = None,
    limite: int = 500,
) -> list[Producao]:
    """Busca no número de série, ID único, nome e código do modelo (RF009). Mais recentes primeiro."""
    consulta = select(Producao).join(Producao.modelo)
    termo = (busca or "").strip()
    if termo:
        padrao = f"%{termo}%"
        consulta = consulta.where(or_(
            Producao.numero_serie.ilike(padrao), Producao.id_unica.ilike(padrao),
            Modelo.nome.ilike(padrao), Modelo.codigo.ilike(padrao),
        ))
    if etapa_id:
        consulta = consulta.where(Producao.etapa_id == etapa_id)
    if modelo_id:
        consulta = consulta.where(Producao.modelo_id == modelo_id)
    return list(sessao.scalars(consulta.order_by(Producao.atualizada_em.desc(), Producao.id.desc()).limit(limite)))


def obter(sessao: Session, producao_id: int) -> Producao:
    p = sessao.get(Producao, producao_id)
    if p is None:
        raise NaoEncontrado("Produção não encontrada.")
    return p


def por_serie(sessao: Session, numero_serie: str) -> Producao | None:
    return sessao.scalar(select(Producao).where(Producao.numero_serie == numero_serie.strip().upper()))


def passagens(sessao: Session, producao_id: int) -> list[Passagem]:
    return list(sessao.scalars(
        select(Passagem).where(Passagem.producao_id == producao_id).order_by(Passagem.registrada_em, Passagem.id)
    ))


def nao_conformidades(sessao: Session, producao_id: int) -> list[NaoConformidade]:
    return list(sessao.scalars(
        select(NaoConformidade).where(NaoConformidade.producao_id == producao_id)
        .order_by(NaoConformidade.registrada_em, NaoConformidade.id)
    ))


def mesmo_modelo(sessao: Session, producao: Producao) -> list[Producao]:
    return list(sessao.scalars(
        select(Producao).where(Producao.modelo_id == producao.modelo_id, Producao.id != producao.id)
        .order_by(Producao.id.desc()).limit(50)
    ))


def proxima_etapa_sugerida(sessao: Session, producao: Producao) -> Etapa | None:
    """Próxima etapa do fluxo principal. Vindo de Parado/Reprovado, volta para a 2ª etapa (retrabalho)."""
    principais = [e for e in listar_etapas(sessao) if e.ordem < ORDEM_LATERAL]
    if not principais:
        return None
    ids = [e.id for e in principais]
    if producao.etapa_id in ids:
        i = ids.index(producao.etapa_id)
        return principais[i + 1] if i + 1 < len(principais) else None
    return principais[1] if len(principais) > 1 else principais[0]


# ---------------------------------------------------------------- escrita


def _usuario(sessao: Session, usuario_id: int | None) -> Usuario | None:
    if usuario_id is None:
        return None
    u = sessao.get(Usuario, usuario_id)
    if u is None or not u.ativo:
        raise ErroNegocio("Responsável não encontrado ou inativo.", status=422)
    return u


def _modelo_ativo(sessao: Session, modelo_id: int) -> Modelo:
    m = sessao.get(Modelo, modelo_id)
    if m is None:
        raise ErroNegocio("Modelo não encontrado.", status=422)
    if not m.ativo:
        raise ErroNegocio(f"O modelo {m.nome} está inativo.", status=422)
    return m


def criar(sessao: Session, executor: Usuario, *, modelo_id: int, responsavel_id: int | None = None) -> Producao:
    _modelo_ativo(sessao, modelo_id)
    principais = listar_etapas(sessao)
    if not principais:
        raise ErroNegocio("Cadastre as etapas de produção antes de iniciar uma produção.", status=409)
    responsavel = _usuario(sessao, responsavel_id) or executor
    agora = tempo.agora()
    # O número de série sai do id gerado pelo banco: grava com um valor provisório e troca no mesmo flush.
    producao = Producao(
        numero_serie=f"TMP-{uuid4().hex[:20]}", id_unica=f"TMP-{uuid4().hex}", modelo_id=modelo_id,
        etapa_id=principais[0].id, responsavel_id=responsavel.id, criado_por_id=executor.id,
        iniciada_em=agora, atualizada_em=agora,
    )
    sessao.add(producao)
    sessao.flush()
    producao.numero_serie = f"{PREFIXO_SERIE}-{producao.id:06d}"
    producao.id_unica = f"PRD-{producao.numero_serie}-{agora.astimezone(tempo.FUSO_FABRICA):%Y%m%d}"
    sessao.add(Passagem(producao_id=producao.id, etapa_id=principais[0].id, usuario_id=executor.id,
                        responsavel_id=responsavel.id, registrada_em=agora, origem=Origem.MANUAL.value))
    sessao.flush()
    sessao.refresh(producao)
    return producao


def alterar(sessao: Session, producao_id: int, *, modelo_id: int, responsavel_id: int | None) -> Producao:
    producao = obter(sessao, producao_id)
    if modelo_id != producao.modelo_id:
        _modelo_ativo(sessao, modelo_id)
        producao.modelo_id = modelo_id
    if responsavel_id:
        producao.responsavel_id = _usuario(sessao, responsavel_id).id
    sessao.flush()
    sessao.refresh(producao)
    return producao


def excluir(sessao: Session, producao_id: int) -> None:
    producao = obter(sessao, producao_id)
    tem_baixa = sessao.scalar(
        select(Baixa.id).join(Baixa.solicitacao).where(Solicitacao.producao_id == producao_id).limit(1)
    )
    if tem_baixa:
        raise ErroNegocio("Há baixas de material nesta produção. Exclua as baixas antes "
                          "(o estoque é devolvido).", status=409)
    for modelo in (NaoConformidade, Solicitacao, Passagem):
        for item in sessao.scalars(select(modelo).where(modelo.producao_id == producao_id)):
            sessao.delete(item)
    sessao.delete(producao)
    sessao.flush()


def avancar_etapa(
    sessao: Session,
    producao_id: int,
    executor: Usuario,
    *,
    etapa_id: int,
    responsavel_id: int | None = None,
    descricao_falha: str | None = None,
    motivo_reprovacao: str | None = None,
    origem: Origem = Origem.MANUAL,
    origem_sistema: str | None = None,
    id_externo: str | None = None,
) -> Producao:
    producao = sessao.get(Producao, producao_id, with_for_update={"of": Producao})
    if producao is None:
        raise NaoEncontrado("Produção não encontrada.")
    etapa = sessao.get(Etapa, etapa_id)
    if etapa is None:
        raise ErroNegocio("Etapa inválida.", status=422)
    if producao.etapa_id == etapa_id:
        raise ErroNegocio("A produção já está nesta etapa.", status=409)
    responsavel = _usuario(sessao, responsavel_id) or sessao.get(Usuario, producao.responsavel_id) or executor
    reprovar = etapa.nome.strip().lower() == ETAPA_REPROVADO.lower()
    falha, motivo = (descricao_falha or "").strip(), (motivo_reprovacao or "").strip()
    if reprovar and not (falha and motivo):
        raise ErroNegocio("Para reprovar, informe a falha encontrada e o motivo da reprovação.", status=422)

    agora = tempo.agora()
    producao.etapa_id = etapa.id
    producao.responsavel_id = responsavel.id
    producao.atualizada_em = agora
    sessao.add(Passagem(producao_id=producao.id, etapa_id=etapa.id, usuario_id=executor.id,
                        responsavel_id=responsavel.id, registrada_em=agora, origem=origem.value))
    if reprovar:
        sessao.add(NaoConformidade(producao_id=producao.id, usuario_id=executor.id, descricao_falha=falha,
                                   motivo_reprovacao=motivo, registrada_em=agora,
                                   origem_sistema=origem_sistema, id_externo=id_externo))
    sessao.flush()
    sessao.refresh(producao)
    return producao


def registrar_nao_conformidade(
    sessao: Session, producao_id: int, executor: Usuario, *, descricao_falha: str, motivo_reprovacao: str
) -> NaoConformidade:
    """RF011: falha encontrada (ex.: no teste) sem mudar a etapa."""
    obter(sessao, producao_id)
    falha, motivo = descricao_falha.strip(), motivo_reprovacao.strip()
    if not (falha and motivo):
        raise ErroNegocio("Informe a falha e o motivo.", status=422)
    nc = NaoConformidade(producao_id=producao_id, usuario_id=executor.id, descricao_falha=falha,
                         motivo_reprovacao=motivo, registrada_em=tempo.agora())
    sessao.add(nc)
    sessao.flush()
    return nc


def _ja_registrada(sessao: Session, origem_sistema: str | None, id_externo: str | None) -> bool:
    if not (origem_sistema and id_externo):
        return False
    return sessao.scalar(select(NaoConformidade.id).where(
        NaoConformidade.origem_sistema == origem_sistema, NaoConformidade.id_externo == id_externo
    )) is not None


def atualizar_por_maquina(
    sessao: Session, executor: Usuario, *, numero_serie: str, etapa_nome: str, maquina: str | None = None
) -> tuple[Producao, bool]:
    """RF017: a máquina informa a etapa. Devolve (produção, alterado). A mesma etapa de novo não grava nada."""
    producao = por_serie(sessao, numero_serie)
    if producao is None:
        raise NaoEncontrado("Número de série não encontrado.")
    etapa = etapa_por_nome(sessao, etapa_nome)
    if etapa is None:
        raise NaoEncontrado(f"Etapa '{etapa_nome}' não cadastrada.")
    if producao.etapa_id == etapa.id:
        return producao, False
    texto = "Reprovado automaticamente pela máquina" + (f" {maquina}" if maquina else "")
    return avancar_etapa(sessao, producao.id, executor, etapa_id=etapa.id, descricao_falha=texto,
                         motivo_reprovacao="Detecção por equipamento", origem=Origem.MAQUINA), True


# ---------------------------------------------------------------- integração com a Qualidade


@dataclass
class ResultadoIntegracao:
    tipo: str  # "sucesso" | "aviso"
    mensagem: str


def aplicar_inspecao(
    sessao: Session,
    executor: Usuario,
    *,
    numero_serie: str,
    situacao: str,
    descricao_falha: str,
    motivo_reprovacao: str,
    origem_sistema: str,
    id_externo: str,
) -> ResultadoIntegracao:
    """Resultado de uma inspeção da Qualidade aplicado à produção (o mesmo de qualidade/integracao.py):

    - REPROVADO      -> etapa Reprovado, com não conformidade (falha e motivo reais);
    - EM_REPROCESSO  -> Reprovado e, em seguida, Em Montagem (o notebook volta para a linha);
    - APROVADO       -> Aprovado, se o notebook ainda não passou dessa etapa (não volta um notebook embalado).
    Reenvio com o mesmo id_externo não reprova de novo. Notebook que já estava em Reprovado não muda de etapa,
    mas a não conformidade da Qualidade é gravada assim mesmo (o sistema antigo descartava essa falha).
    """
    producao = por_serie(sessao, numero_serie)
    if producao is None:
        return ResultadoIntegracao("aviso", f"Rastreabilidade: o notebook {numero_serie} não está em produção.")
    serie = producao.numero_serie

    def mover(nome: str, **extra) -> None:
        etapa = etapa_por_nome(sessao, nome)
        if etapa is None:
            raise ErroNegocio(f"A etapa '{nome}' não está cadastrada na Rastreabilidade.", status=409)
        if producao.etapa_id != etapa.id:
            avancar_etapa(sessao, producao.id, executor, etapa_id=etapa.id, origem=Origem.QUALIDADE, **extra)

    if situacao in ("REPROVADO", "EM_REPROCESSO"):
        if _ja_registrada(sessao, origem_sistema, id_externo):
            return ResultadoIntegracao("sucesso", f"Rastreabilidade: a reprovação de {serie} já estava registrada.")
        ja_reprovado = producao.etapa.nome.strip().lower() == ETAPA_REPROVADO.lower()
        if ja_reprovado:
            nc = registrar_nao_conformidade(sessao, producao.id, executor, descricao_falha=descricao_falha,
                                            motivo_reprovacao=motivo_reprovacao)
            nc.origem_sistema, nc.id_externo = origem_sistema, id_externo
            sessao.flush()
        else:
            mover(ETAPA_REPROVADO, descricao_falha=descricao_falha, motivo_reprovacao=motivo_reprovacao,
                  origem_sistema=origem_sistema, id_externo=id_externo)
        if situacao == "REPROVADO":
            if ja_reprovado:
                return ResultadoIntegracao("sucesso", f"Rastreabilidade: {serie} já estava Reprovado; "
                                                      "não conformidade registrada.")
            return ResultadoIntegracao("sucesso", f"Rastreabilidade: {serie} marcado como Reprovado.")
        mover(ETAPA_MONTAGEM)
        return ResultadoIntegracao("sucesso", f"Rastreabilidade: {serie} reprovado e devolvido para Em Montagem (reprocesso).")

    aprovado = etapa_por_nome(sessao, ETAPA_APROVADO)
    atual = producao.etapa
    ja_passou = aprovado is not None and atual.ordem < ORDEM_LATERAL and atual.ordem >= aprovado.ordem
    if ja_passou:
        return ResultadoIntegracao("sucesso", f"Rastreabilidade: {serie} já está em {atual.nome}; nada a alterar.")
    mover(ETAPA_APROVADO)
    return ResultadoIntegracao("sucesso", f"Rastreabilidade: {serie} marcado como Aprovado.")
