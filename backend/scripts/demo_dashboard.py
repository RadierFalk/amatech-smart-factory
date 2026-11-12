"""Dados do Dashboard para um banco novo, usados pelo seed_demo: turnos, limites do semáforo e tipos de perda
(os mesmos do sistema antigo) e, se já houver produção de demonstração na RAS, metas e algumas perdas.

As metas saem da própria produção de demonstração (um pouco acima em parte das combinações), para o painel
mostrar o semáforo nas três cores.
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.modulos.dashboard import calculo
from app.modulos.dashboard.constantes import LIMITES_PADRAO, TIPOS_PERDA_PADRAO, TURNOS_PADRAO
from app.modulos.dashboard.modelos import Limite, Meta, Perda, TipoPerda, Turno
from app.modulos.qualidade.modelos import Estacao
from app.modulos.usuarios.modelos import Usuario


def popular(sessao: Session, supervisor: Usuario | None) -> list[str]:
    feito = []
    if not sessao.scalar(select(Turno.id).limit(1)):
        sessao.add_all(Turno(nome=n, hora_inicio=i, hora_fim=f) for n, i, f in TURNOS_PADRAO)
        feito.append(f"dsh.turnos: {len(TURNOS_PADRAO)} turnos (06h-14h e 14h-22h)")
    if not sessao.scalar(select(Limite.indicador).limit(1)):
        sessao.add_all(Limite(indicador=i.value, limite_verde=v, limite_amarelo=a, sentido=s.value)
                       for i, v, a, s in LIMITES_PADRAO)
        feito.append("dsh.limites: limites do semáforo dos 3 indicadores")
    if not sessao.scalar(select(TipoPerda.id).limit(1)):
        sessao.add_all(TipoPerda(nome=n) for n in TIPOS_PERDA_PADRAO)
        feito.append(f"dsh.tipos_perda: {len(TIPOS_PERDA_PADRAO)} tipos")
    sessao.flush()
    if supervisor is None or sessao.scalar(select(Meta.id).limit(1)):
        return feito

    hoje = calculo.hoje_na_fabrica()
    filtro = calculo.Filtro(de=hoje - timedelta(days=6), ate=hoje)
    producao = calculo.producao(sessao, filtro, calculo.Turnos(sessao))
    agora = tempo.agora()
    for (dia, turno_id, modelo_id), v in sorted(producao.items()):
        realizada = v["aprovada"] + v["reprovada"]
        extra = 1 if (dia.day + modelo_id + turno_id) % 3 == 0 else 0
        sessao.add(Meta(data=dia, turno_id=turno_id, modelo_id=modelo_id, quantidade=max(1, realizada) + extra,
                        registrado_por_id=supervisor.id, registrado_em=agora))
    feito.append(f"dsh.metas: {len(producao)} metas dos últimos 7 dias")

    tipos = list(sessao.scalars(select(TipoPerda).order_by(TipoPerda.id)))
    estacao = sessao.scalar(select(Estacao).where(Estacao.nome == "Montagem Final")) or sessao.scalar(select(Estacao))
    turno = sessao.scalar(select(Turno).order_by(Turno.hora_inicio))
    if estacao and producao:
        for k, (dia, _, modelo_id) in enumerate(sorted(producao)[:4]):
            sessao.add(Perda(data=dia, turno_id=turno.id, estacao_id=estacao.id, modelo_id=modelo_id,
                             tipo_perda_id=tipos[k % len(tipos)].id, quantidade=k + 1,
                             observacao="Registro de demonstração", registrado_por_id=supervisor.id, registrado_em=agora))
        feito.append("dsh.perdas: 4 perdas de demonstração")
    sessao.flush()
    return feito
