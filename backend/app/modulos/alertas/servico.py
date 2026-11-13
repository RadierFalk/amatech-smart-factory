"""Alertas: as situações abertas da fábrica, conferidas a cada consulta do sino (a tela consulta a cada 30 s).

`sincronizar` compara o que está aberto agora com os alertas ativos: cria os que faltam, atualiza o detalhe dos que
mudaram (ex.: o estoque) e resolve os que deixaram de existir. Assim todo caminho que muda os dados (telas, máquinas,
migração) é coberto sem gatilho em cada operação, e "parada há mais de 30 min" funciona com o passar do tempo.

| Tipo                 | Situação                                                   | Quem recebe                       |
|----------------------|------------------------------------------------------------|-----------------------------------|
| CHAMADO_ABERTO       | OS aberta (ninguém assumiu) com prioridade alta ou crítica | Técnico, Supervisor, Administrador|
| PARADA_SEM_TECNICO   | Máquina parada há mais de 30 min com a OS ainda na fila    | Supervisor, Administrador         |
| ESTOQUE_INSUFICIENTE | Estoque menor que o que falta entregar nos pedidos abertos | Almoxarife, Supervisor, Adm.      |
| OCORRENCIA_CRITICA   | Ocorrência crítica dos últimos 7 dias ainda não resolvida  | Inspetor, Supervisor, Adm.        |
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import insert, select, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.rbac import Perfil
from app.modulos.alertas.modelos import Alerta, AlertaLido
from app.modulos.manutencao.constantes import Prioridade, StatusChamado, StatusEquipamento
from app.modulos.manutencao.modelos import Chamado
from app.modulos.qualidade.constantes import ROTULOS_STATUS, Classificacao, StatusOcorrencia
from app.modulos.qualidade.modelos import Ocorrencia
from app.modulos.rastreabilidade.constantes import SOLICITACAO_ABERTA
from app.modulos.rastreabilidade.modelos import Componente, Solicitacao
from app.modulos.usuarios.modelos import Usuario

P = Perfil
MINUTOS_SEM_TECNICO = 30
DIAS_OCORRENCIA_CRITICA = 7
HORAS_RESOLVIDOS_VISIVEIS = 24
PRIORIDADES_ALERTA = (Prioridade.ALTA.value, Prioridade.CRITICA.value)
ROTULO_PRIORIDADE = {Prioridade.ALTA.value: "alta", Prioridade.CRITICA.value: "crítica"}


@dataclass
class Situacao:
    tipo: str
    modulo: str
    titulo: str
    detalhe: str
    link: str
    perfis: tuple[Perfil, ...]


def _hora(instante: datetime) -> str:
    return tempo.utc(instante).astimezone(tempo.FUSO_FABRICA).strftime("%d/%m %H:%M")


def situacoes_abertas(sessao: Session) -> dict[str, Situacao]:
    """O que deveria ter alerta agora, por chave."""
    agora = tempo.agora()
    abertas: dict[str, Situacao] = {}

    chamados = sessao.scalars(select(Chamado).join(Chamado.equipamento)
                              .where(Chamado.status_chamado == StatusChamado.ABERTO.value))
    for c in chamados:
        tag = c.equipamento.codigo_tag
        if c.prioridade in PRIORIDADES_ALERTA:
            abertas[f"chamado:{c.id}"] = Situacao(
                "CHAMADO_ABERTO", "MNT", f"OS #{c.id} aberta: {tag}",
                f"Prioridade {ROTULO_PRIORIDADE[c.prioridade]} · {c.descricao_falha}"[:300],
                f"/manutencao/ordens/{c.id}", (P.TECNICO, P.SUPERVISOR, P.ADMINISTRADOR))
        parada_ha = agora - tempo.utc(c.data_hora_abertura)
        if c.equipamento.status_operacional == StatusEquipamento.PARADA.value and parada_ha >= timedelta(minutes=MINUTOS_SEM_TECNICO):
            abertas[f"parada:{c.id}"] = Situacao(
                "PARADA_SEM_TECNICO", "MNT", f"{tag} parada há mais de {MINUTOS_SEM_TECNICO} min sem técnico",
                f"OS #{c.id} aberta em {_hora(c.data_hora_abertura)} e ainda na fila · {c.equipamento.nome}"[:300],
                "/manutencao/fila", (P.SUPERVISOR, P.ADMINISTRADOR))

    falta: Counter = Counter()
    for s in sessao.scalars(select(Solicitacao).where(Solicitacao.status.in_([s.value for s in SOLICITACAO_ABERTA]))):
        falta[s.componente_id] += max(s.quantidade - s.quantidade_baixada, 0)
    if falta:
        for comp in sessao.scalars(select(Componente).where(Componente.id.in_(list(falta)), Componente.ativo.is_(True))):
            if comp.estoque < falta[comp.id]:
                abertas[f"estoque:{comp.id}"] = Situacao(
                    "ESTOQUE_INSUFICIENTE", "RAS", f"{comp.sku} sem estoque suficiente",
                    f"{comp.estoque} em estoque para {falta[comp.id]} pedido(s) em aberto · {comp.nome}"[:300],
                    "/rastreabilidade/materiais", (P.ALMOXARIFE, P.SUPERVISOR, P.ADMINISTRADOR))

    desde = agora - timedelta(days=DIAS_OCORRENCIA_CRITICA)
    criticas = sessao.scalars(select(Ocorrencia).where(
        Ocorrencia.classificacao == Classificacao.CRITICO.value, Ocorrencia.oculta.is_(False),
        Ocorrencia.status != StatusOcorrencia.RESOLVIDA.value, Ocorrencia.ocorrida_em >= desde))
    for o in criticas:
        abertas[f"ocorrencia:{o.id}"] = Situacao(
            "OCORRENCIA_CRITICA", "QLD", f"Ocorrência crítica #{o.id}: {o.tipo_defeito.nome}",
            f"{o.produto.numero_serie} · {o.estacao.nome} · {ROTULOS_STATUS[StatusOcorrencia(o.status)]}"[:300],
            "/qualidade/historico", (P.INSPETOR, P.SUPERVISOR, P.ADMINISTRADOR))
    return abertas


def sincronizar(sessao: Session) -> None:
    """Cria, atualiza e resolve os alertas para refletirem as situações abertas agora."""
    agora = tempo.agora()
    abertas = situacoes_abertas(sessao)
    ativos = {a.chave: a for a in sessao.scalars(select(Alerta).where(Alerta.ativo.is_(True)))}
    for chave, alerta in ativos.items():
        situacao = abertas.get(chave)
        if situacao is None:
            alerta.ativo, alerta.resolvido_em = False, agora
        elif (alerta.titulo, alerta.detalhe) != (situacao.titulo, situacao.detalhe):
            alerta.titulo, alerta.detalhe = situacao.titulo, situacao.detalhe
    novos = [
        {"tipo": s.tipo, "modulo": s.modulo, "titulo": s.titulo, "detalhe": s.detalhe, "link": s.link,
         "perfis": "|".join(p.value for p in s.perfis), "chave": chave, "ativo": True, "criado_em": agora}
        for chave, s in abertas.items() if chave not in ativos
    ]
    sessao.flush()
    if novos:
        # Duas telas consultando ao mesmo tempo: o índice único (chave, só ativos) deixa entrar um alerta só.
        dialeto = postgresql if sessao.get_bind().dialect.name == "postgresql" else sqlite
        comando = dialeto.insert(Alerta).values(novos).on_conflict_do_nothing(
            index_elements=["chave"], index_where=text("ativo"))
        sessao.execute(comando)


def visiveis(sessao: Session, usuario: Usuario) -> tuple[list[tuple[Alerta, bool]], int]:
    """Alertas do perfil da pessoa: os ativos e os resolvidos nas últimas 24 h, mais recentes primeiro, com o
    "já li". Devolve também quantos ativos ela ainda não leu."""
    desde = tempo.agora() - timedelta(hours=HORAS_RESOLVIDOS_VISIVEIS)
    candidatos = sessao.scalars(
        select(Alerta).where((Alerta.ativo.is_(True)) | (Alerta.resolvido_em >= desde))
        .order_by(Alerta.ativo.desc(), Alerta.criado_em.desc(), Alerta.id.desc()).limit(300))
    meus = [a for a in candidatos if usuario.perfil in a.perfis.split("|")][:50]
    lidos = set(sessao.scalars(select(AlertaLido.alerta_id).where(
        AlertaLido.usuario_id == usuario.id, AlertaLido.alerta_id.in_([a.id for a in meus]))))
    nao_lidos = sum(1 for a in meus if a.ativo and a.id not in lidos)
    return [(a, a.id in lidos) for a in meus], nao_lidos


def marcar_lidos(sessao: Session, usuario: Usuario, ids: list[int] | None) -> int:
    """Marca como lidos os alertas indicados (ou todos os visíveis). Devolve quantos foram marcados agora."""
    lista, _ = visiveis(sessao, usuario)
    alvo = [a.id for a, lido in lista if not lido and (ids is None or a.id in ids)]
    if alvo:
        agora = tempo.agora()
        sessao.execute(insert(AlertaLido), [{"alerta_id": i, "usuario_id": usuario.id, "lido_em": agora} for i in alvo])
    return len(alvo)

