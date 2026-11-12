"""Ocorrências de defeito e cadastros da Qualidade (portado de qualidade/ocorrencia.py e banco.py).

Regras:
- O responsável pela ocorrência é sempre quem a registrou (o usuário logado); editar não troca o responsável.
- Ocorrência não é apagada: é ocultada e some das listas e dos indicadores.
- Produto, estação, tipo de defeito e máquina precisam existir e estar ativos para um registro novo.
- O resultado vai para a Rastreabilidade (etapa do notebook com o mesmo número de série).
- Defeito causado pela máquina abre chamado na Manutenção (prioridade pela classificação). Se a Manutenção
  recusar (ex.: a máquina já tem OS ativa, RN02), a ocorrência é gravada assim mesmo e a recusa vira aviso.
- Datas: gravadas em UTC; filtros por dia usam o dia da fábrica (Manaus).

Quem pode chamar cada função (persona) é decidido nas rotas.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import ErroNegocio, NaoEncontrado
from app.modulos.manutencao import servico as servico_mnt
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.constantes import (
    ORIGEM_CHAMADO,
    PRIORIDADE_CHAMADO,
    ROTULOS_CLASSIFICACAO,
    Classificacao,
    SituacaoProduto,
    StatusOcorrencia,
    id_externo,
)
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.rastreabilidade import producao as servico_ras
from app.modulos.usuarios.modelos import Usuario

# ---------------------------------------------------------------- cadastros (produtos, estações, tipos)

CADASTROS = {
    "produto": (Produto, "numero_serie", "o produto"),
    "estacao": (Estacao, "nome", "a estação"),
    "tipo_defeito": (TipoDefeito, "nome", "o tipo de defeito"),
}


def listar_cadastro(sessao: Session, tipo: str, incluir_inativos: bool = False) -> list:
    modelo, campo, _ = CADASTROS[tipo]
    consulta = select(modelo)
    if not incluir_inativos:
        consulta = consulta.where(modelo.ativo.is_(True))
    return list(sessao.scalars(consulta.order_by(getattr(modelo, campo))))


def _normalizar(tipo: str, valores: dict) -> dict:
    valores = {k: (v.strip() if isinstance(v, str) else v) for k, v in valores.items()}
    if tipo == "produto" and valores.get("numero_serie"):
        valores["numero_serie"] = valores["numero_serie"].upper()
    return valores


def _exigir_unico(sessao: Session, tipo: str, valor: str, exceto_id: int | None = None) -> None:
    modelo, campo, artigo = CADASTROS[tipo]
    coluna = getattr(modelo, campo)
    consulta = select(modelo.id).where(coluna.ilike(valor) if campo == "nome" else coluna == valor)
    if exceto_id is not None:
        consulta = consulta.where(modelo.id != exceto_id)
    if sessao.scalar(consulta):
        raise ErroNegocio(f"Já existe {artigo} '{valor}'.", status=409)


def criar_cadastro(sessao: Session, tipo: str, **valores):
    modelo, campo, _ = CADASTROS[tipo]
    valores = _normalizar(tipo, valores)
    _exigir_unico(sessao, tipo, valores[campo])
    item = modelo(**valores)
    sessao.add(item)
    sessao.flush()
    return item


def alterar_cadastro(sessao: Session, tipo: str, item_id: int, **valores):
    modelo, campo, artigo = CADASTROS[tipo]
    item = sessao.get(modelo, item_id)
    if item is None:
        raise NaoEncontrado(f"Não encontrei {artigo} #{item_id}.")
    valores = _normalizar(tipo, valores)
    if campo in valores:
        _exigir_unico(sessao, tipo, valores[campo], exceto_id=item_id)
    for chave, valor in valores.items():
        setattr(item, chave, valor)
    sessao.flush()
    return item


def listar_maquinas(sessao: Session) -> list[Equipamento]:
    """Máquinas ativas da Manutenção (a Qualidade não tem acesso às rotas /api/mnt)."""
    return list(sessao.scalars(select(Equipamento).where(Equipamento.ativo.is_(True)).order_by(Equipamento.codigo_tag)))


# ---------------------------------------------------------------- ocorrências


@dataclass
class DadosOcorrencia:
    ocorrida_em: datetime
    classificacao: Classificacao
    situacao_produto: SituacaoProduto
    status: StatusOcorrencia
    observacao: str
    acao_realizada: str
    produto_id: int
    estacao_id: int
    tipo_defeito_id: int
    equipamento_id: int


@dataclass
class Aviso:
    tipo: str  # "sucesso" | "aviso"
    mensagem: str


def _referencia(sessao: Session, modelo, item_id: int, nome: str, *, exigir_ativo: bool):
    item = sessao.get(modelo, item_id)
    if item is None:
        raise ErroNegocio(f"{nome} não encontrado(a).", status=422)
    if exigir_ativo and not item.ativo:
        raise ErroNegocio(f"{nome} está inativo(a): escolha outro(a).", status=422)
    return item


def _validar(sessao: Session, dados: DadosOcorrencia, *, atual: Ocorrencia | None = None) -> datetime:
    """Confere as referências. Na edição, a referência que não mudou pode ter sido inativada depois."""
    def exigir(modelo, campo: str, nome: str) -> None:
        novo = getattr(dados, campo)
        _referencia(sessao, modelo, novo, nome, exigir_ativo=atual is None or getattr(atual, campo) != novo)

    exigir(Produto, "produto_id", "Produto")
    exigir(Estacao, "estacao_id", "Estação")
    exigir(TipoDefeito, "tipo_defeito_id", "Tipo de defeito")
    exigir(Equipamento, "equipamento_id", "Máquina")
    for campo, rotulo in (("observacao", "A observação"), ("acao_realizada", "A ação realizada")):
        if not getattr(dados, campo).strip():
            raise ErroNegocio(f"{rotulo} é obrigatória.", status=422)

    quando = dados.ocorrida_em
    if quando.tzinfo is None:  # sem fuso: hora da fábrica
        quando = quando.replace(tzinfo=tempo.FUSO_FABRICA)
    quando = tempo.utc(quando)
    if quando > tempo.agora() + timedelta(minutes=5):
        raise ErroNegocio("A data da ocorrência não pode estar no futuro.", status=422)
    return quando


def _aplicar(oc: Ocorrencia, dados: DadosOcorrencia, quando: datetime) -> None:
    oc.ocorrida_em = quando
    oc.classificacao = dados.classificacao.value
    oc.situacao_produto = dados.situacao_produto.value
    oc.status = dados.status.value
    oc.observacao = dados.observacao.strip()
    oc.acao_realizada = dados.acao_realizada.strip()
    oc.produto_id = dados.produto_id
    oc.estacao_id = dados.estacao_id
    oc.tipo_defeito_id = dados.tipo_defeito_id
    oc.equipamento_id = dados.equipamento_id


def registrar(
    sessao: Session, executor: Usuario, dados: DadosOcorrencia, *, abrir_chamado: bool = False
) -> tuple[Ocorrencia, list[Aviso]]:
    quando = _validar(sessao, dados)
    oc = Ocorrencia(responsavel_id=executor.id, oculta=False)
    _aplicar(oc, dados, quando)
    sessao.add(oc)
    sessao.flush()
    sessao.refresh(oc)
    avisos = [informar_rastreabilidade(sessao, oc, executor)]
    if abrir_chamado:
        avisos.append(abrir_chamado_manutencao(sessao, oc, executor))
    return oc, avisos


def obter(sessao: Session, ocorrencia_id: int) -> Ocorrencia:
    oc = sessao.get(Ocorrencia, ocorrencia_id)
    if oc is None or oc.oculta:
        raise NaoEncontrado(f"Ocorrência #{ocorrencia_id} não encontrada.")
    return oc


def editar(sessao: Session, ocorrencia_id: int, dados: DadosOcorrencia) -> Ocorrencia:
    """Edita os dados; o responsável continua sendo quem registrou."""
    oc = obter(sessao, ocorrencia_id)
    quando = _validar(sessao, dados, atual=oc)
    _aplicar(oc, dados, quando)
    sessao.flush()
    sessao.refresh(oc)
    return oc


def ocultar(sessao: Session, ocorrencia_id: int) -> None:
    oc = obter(sessao, ocorrencia_id)
    oc.oculta = True
    sessao.flush()


def informar_rastreabilidade(sessao: Session, oc: Ocorrencia, executor: Usuario) -> Aviso:
    """Leva o resultado da inspeção à produção do notebook (mesmo número de série) na Rastreabilidade.

    Reprovado -> etapa Reprovado (com não conformidade); Em reprocesso -> Reprovado e volta para Em Montagem;
    Aprovado -> Aprovado, se ainda não passou dessa etapa. Num savepoint: se a RAS recusar, vira aviso.
    """
    classificacao = ROTULOS_CLASSIFICACAO[Classificacao(oc.classificacao)]
    try:
        with sessao.begin_nested():
            r = servico_ras.aplicar_inspecao(
                sessao,
                executor,
                numero_serie=oc.produto.numero_serie,
                situacao=oc.situacao_produto,
                descricao_falha=oc.observacao,
                motivo_reprovacao=f"{oc.tipo_defeito.nome} ({classificacao})",
                origem_sistema=ORIGEM_CHAMADO,
                id_externo=id_externo(oc.id),
            )
    except ErroNegocio as e:
        return Aviso("aviso", f"Rastreabilidade: o notebook não foi atualizado. {e.mensagem}")
    return Aviso(r.tipo, r.mensagem)


def abrir_chamado_manutencao(sessao: Session, oc: Ocorrencia, executor: Usuario) -> Aviso:
    """Abre (ou reaproveita) o chamado da Manutenção para a máquina da ocorrência.

    Roda num savepoint: se a Manutenção recusar, só o chamado é desfeito, e a ocorrência fica gravada.
    """
    classificacao = Classificacao(oc.classificacao)
    descricao = (
        f"{oc.tipo_defeito.nome} em {oc.produto.numero_serie}: {oc.observacao} "
        f"(ocorrência {id_externo(oc.id)} da Qualidade, {ROTULOS_CLASSIFICACAO[classificacao].lower()})"
    )
    try:
        with sessao.begin_nested():
            chamado, criado = servico_mnt.abrir_chamado_por_tag(
                sessao,
                equipamento_tag=oc.equipamento.codigo_tag,
                executor=executor,
                descricao_falha=descricao[:2000],
                prioridade=PRIORIDADE_CHAMADO[classificacao],
                origem_sistema=ORIGEM_CHAMADO,
                id_externo=id_externo(oc.id),
            )
    except ErroNegocio as e:
        return Aviso("aviso", f"Manutenção: o chamado não foi aberto. {e.mensagem}")
    if not criado:
        return Aviso("sucesso", f"Manutenção: o chamado OS #{chamado.id} desta ocorrência já estava aberto.")
    return Aviso("sucesso", f"Manutenção: chamado OS #{chamado.id} aberto para a máquina {oc.equipamento.codigo_tag}.")


def chamados_das_ocorrencias(sessao: Session, ids: list[int]) -> dict[int, Chamado]:
    """Chamado da Manutenção aberto para cada ocorrência (uma consulta para a lista toda)."""
    if not ids:
        return {}
    por_externo = {id_externo(i): i for i in ids}
    chamados = sessao.scalars(
        select(Chamado).where(Chamado.origem_sistema == ORIGEM_CHAMADO, Chamado.id_externo.in_(list(por_externo)))
    )
    return {por_externo[c.id_externo]: c for c in chamados}


def inicio_do_dia(dia: date) -> datetime:
    """00:00 do dia da fábrica (Manaus), em UTC."""
    return tempo.utc(datetime.combine(dia, time(), tempo.FUSO_FABRICA))


def listar(
    sessao: Session,
    *,
    busca: str | None = None,
    classificacao: Classificacao | None = None,
    situacao: SituacaoProduto | None = None,
    status: StatusOcorrencia | None = None,
    estacao_id: int | None = None,
    tipo_defeito_id: int | None = None,
    equipamento_id: int | None = None,
    de: date | None = None,
    ate: date | None = None,
    limite: int = 500,
) -> list[Ocorrencia]:
    """Ocorrências visíveis, da mais recente para a mais antiga."""
    consulta = (
        select(Ocorrencia)
        .join(Ocorrencia.produto)
        .join(Ocorrencia.estacao)
        .join(Ocorrencia.tipo_defeito)
        .join(Ocorrencia.equipamento)
        .join(Ocorrencia.responsavel)
        .where(Ocorrencia.oculta.is_(False))
    )
    if classificacao:
        consulta = consulta.where(Ocorrencia.classificacao == classificacao.value)
    if situacao:
        consulta = consulta.where(Ocorrencia.situacao_produto == situacao.value)
    if status:
        consulta = consulta.where(Ocorrencia.status == status.value)
    if estacao_id:
        consulta = consulta.where(Ocorrencia.estacao_id == estacao_id)
    if tipo_defeito_id:
        consulta = consulta.where(Ocorrencia.tipo_defeito_id == tipo_defeito_id)
    if equipamento_id:
        consulta = consulta.where(Ocorrencia.equipamento_id == equipamento_id)
    if de:
        consulta = consulta.where(Ocorrencia.ocorrida_em >= inicio_do_dia(de))
    if ate:
        consulta = consulta.where(Ocorrencia.ocorrida_em < inicio_do_dia(ate + timedelta(days=1)))
    termo = (busca or "").strip()
    if termo:
        padrao = f"%{termo}%"
        condicoes = [
            Produto.numero_serie.ilike(padrao),
            Produto.modelo.ilike(padrao),
            Estacao.nome.ilike(padrao),
            TipoDefeito.nome.ilike(padrao),
            Equipamento.codigo_tag.ilike(padrao),
            Equipamento.nome.ilike(padrao),
            Usuario.nome.ilike(padrao),
            Ocorrencia.observacao.ilike(padrao),
            Ocorrencia.acao_realizada.ilike(padrao),
            cast(Ocorrencia.id, String) == termo.lstrip("#"),
        ]
        consulta = consulta.where(or_(*condicoes))
    return list(sessao.scalars(consulta.order_by(Ocorrencia.ocorrida_em.desc(), Ocorrencia.id.desc()).limit(limite)))
