"""Rotas do módulo de Manutenção (/api/mnt).

Permissões por persona (seguem a matriz do portal antigo):

| Ação                                              | Personas                                  |
|---------------------------------------------------|-------------------------------------------|
| Ver máquinas, chamados, peças, opções             | todas com acesso ao módulo (rbac.py)      |
| Abrir chamado corretivo                           | Operador, Técnico, Supervisor, Administrador |
| Fila, assumir, laudo, peças, programar preventiva | Técnico, Administrador                    |
| Concluir OS                                       | Técnico responsável; Supervisor e Adm.    |
| Cancelar OS, cadastros, indicadores, auditoria    | Supervisor, Administrador                 |
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import SessaoDep, UsuarioAtual, exigir_modulo, exigir_perfis
from app.core.rbac import Modulo, Perfil
from app.modulos.manutencao import cadastros, indicadores, servico
from app.modulos.manutencao.constantes import (
    CAUSAS_RAIZ_PADRAO,
    ROTULOS_STATUS_EQUIPAMENTO,
    SETORES_PADRAO,
    Prioridade,
    StatusChamado,
    TipoManutencao,
)
from app.modulos.manutencao.esquemas import (
    AuditoriaSaida,
    ChamadoAbrir,
    ChamadoCancelar,
    ChamadoConcluir,
    ChamadoSaida,
    EquipamentoAlterar,
    EquipamentoCriar,
    EquipamentoSaida,
    LaudoSalvar,
    OpcoesSaida,
    PecaAdicionar,
    PecaAlterar,
    PecaCriar,
    PecaSaida,
    PreventivaProgramar,
)
from app.modulos.usuarios.modelos import Usuario

P = Perfil
ABRIR = (P.OPERADOR, P.TECNICO, P.SUPERVISOR, P.ADMINISTRADOR)
TECNICA = (P.TECNICO, P.ADMINISTRADOR)
GESTAO = (P.SUPERVISOR, P.ADMINISTRADOR)
CONCLUIR = (P.TECNICO, P.SUPERVISOR, P.ADMINISTRADOR)


def _eh_gestao(usuario: Usuario) -> bool:
    """Gestão pode concluir/alterar OS de qualquer técnico (exceção da RN03)."""
    return Perfil(usuario.perfil) in GESTAO


def _pode(*perfis: Perfil):
    return Depends(exigir_perfis(*perfis))


rotas = APIRouter(prefix="/api/mnt", tags=["Manutenção (MNT)"], dependencies=[Depends(exigir_modulo(Modulo.MANUTENCAO))])


# ---------------------------------------------------------------- apoio


@rotas.get("/opcoes", response_model=OpcoesSaida)
def opcoes(sessao: SessaoDep, usuario: UsuarioAtual):
    perfil = Perfil(usuario.perfil)
    setores = sorted(set(SETORES_PADRAO) | set(cadastros.listar_setores(sessao)))
    return OpcoesSaida(
        prioridades=list(Prioridade),
        tipos_manutencao=list(TipoManutencao),
        status_chamado=list(StatusChamado),
        status_equipamento={k.value: v for k, v in ROTULOS_STATUS_EQUIPAMENTO.items()},
        setores=setores,
        causas_raiz=CAUSAS_RAIZ_PADRAO,
        permissoes={
            "abrir_chamado": perfil in ABRIR,
            "atender": perfil in TECNICA,
            "concluir_qualquer": perfil in GESTAO,
            "cancelar": perfil in GESTAO,
            "cadastros": perfil in GESTAO,
            "indicadores": perfil in GESTAO,
        },
    )


# ---------------------------------------------------------------- máquinas e peças


@rotas.get("/equipamentos", response_model=list[EquipamentoSaida])
def listar_equipamentos(sessao: SessaoDep, setor: str | None = None, incluir_inativos: bool = False):
    return [EquipamentoSaida.de(e, a) for e, a in cadastros.listar_equipamentos(sessao, setor, incluir_inativos)]


@rotas.post(
    "/equipamentos", response_model=EquipamentoSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*GESTAO)]
)
def criar_equipamento(dados: EquipamentoCriar, sessao: SessaoDep):
    return EquipamentoSaida.de(cadastros.criar_equipamento(sessao, **dados.model_dump()))


@rotas.patch("/equipamentos/{equipamento_id}", response_model=EquipamentoSaida, dependencies=[_pode(*GESTAO)])
def alterar_equipamento(equipamento_id: int, dados: EquipamentoAlterar, sessao: SessaoDep):
    return EquipamentoSaida.de(cadastros.alterar_equipamento(sessao, equipamento_id, **dados.model_dump(exclude_unset=True)))


@rotas.get("/pecas", response_model=list[PecaSaida])
def listar_pecas(sessao: SessaoDep, incluir_inativas: bool = False):
    return [PecaSaida.de(p) for p in cadastros.listar_pecas(sessao, incluir_inativas)]


@rotas.post("/pecas", response_model=PecaSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*GESTAO)])
def criar_peca(dados: PecaCriar, sessao: SessaoDep):
    return PecaSaida.de(cadastros.criar_peca(sessao, **dados.model_dump()))


@rotas.patch("/pecas/{peca_id}", response_model=PecaSaida, dependencies=[_pode(*GESTAO)])
def alterar_peca(peca_id: int, dados: PecaAlterar, sessao: SessaoDep):
    return PecaSaida.de(cadastros.alterar_peca(sessao, peca_id, **dados.model_dump(exclude_unset=True)))


# ---------------------------------------------------------------- chamados


@rotas.post("/chamados", response_model=ChamadoSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*ABRIR)])
def abrir_chamado(dados: ChamadoAbrir, sessao: SessaoDep, usuario: UsuarioAtual):
    """Chamado corretivo: a máquina fica PARADA até a conclusão."""
    chamado = servico.abrir_chamado(
        sessao,
        equipamento_id=dados.equipamento_id,
        executor=usuario,
        prioridade=dados.prioridade,
        descricao_falha=dados.descricao_falha,
    )
    return ChamadoSaida.de(chamado)


@rotas.post("/preventivas", response_model=ChamadoSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*TECNICA)])
def programar_preventiva(dados: PreventivaProgramar, sessao: SessaoDep, usuario: UsuarioAtual):
    """Preventiva programada: entra na fila sem parar a máquina; para quando o técnico assume."""
    chamado = servico.abrir_chamado(
        sessao,
        equipamento_id=dados.equipamento_id,
        executor=usuario,
        prioridade=dados.prioridade,
        descricao_falha=dados.descricao_falha,
        tipo_manutencao=TipoManutencao.PREVENTIVA,
        parar_maquina=False,
    )
    return ChamadoSaida.de(chamado)


@rotas.get("/chamados/fila", response_model=list[ChamadoSaida], dependencies=[_pode(P.TECNICO, P.SUPERVISOR, P.ADMINISTRADOR)])
def fila(sessao: SessaoDep, setor: str | None = None):
    return [ChamadoSaida.de(c) for c in servico.listar_fila(sessao, setor)]


@rotas.get("/chamados", response_model=list[ChamadoSaida])
def listar_chamados(
    sessao: SessaoDep,
    usuario: UsuarioAtual,
    status_chamado: Annotated[list[StatusChamado] | None, Query(alias="status")] = None,
    tipo: TipoManutencao | None = None,
    prioridade: Prioridade | None = None,
    setor: str | None = None,
    equipamento_id: int | None = None,
    tecnico_id: int | None = None,
    meus_abertos: bool = Query(False, description="Só os chamados que eu abri"),
    meus_atendimentos: bool = Query(False, description="Só as OS em que sou o técnico"),
    de: date | None = None,
    ate: date | None = None,
    busca: str | None = None,
    limite: int = Query(500, ge=1, le=2000),
):
    chamados = servico.listar_chamados(
        sessao,
        status=status_chamado,
        tipo=tipo,
        prioridade=prioridade,
        setor=setor,
        equipamento_id=equipamento_id,
        tecnico_id=usuario.id if meus_atendimentos else tecnico_id,
        operador_id=usuario.id if meus_abertos else None,
        de=de,
        ate=ate,
        busca=busca,
        limite=limite,
    )
    return [ChamadoSaida.de(c) for c in chamados]


@rotas.get("/chamados/{chamado_id}", response_model=ChamadoSaida)
def obter_chamado(chamado_id: int, sessao: SessaoDep):
    return ChamadoSaida.de(servico.obter_chamado(sessao, chamado_id))


@rotas.post("/chamados/{chamado_id}/assumir", response_model=ChamadoSaida, dependencies=[_pode(*TECNICA)])
def assumir(chamado_id: int, sessao: SessaoDep, usuario: UsuarioAtual):
    return ChamadoSaida.de(servico.assumir_chamado(sessao, chamado_id, usuario))


@rotas.put("/chamados/{chamado_id}/laudo", response_model=ChamadoSaida, dependencies=[_pode(*TECNICA)])
def salvar_laudo(chamado_id: int, dados: LaudoSalvar, sessao: SessaoDep, usuario: UsuarioAtual):
    return ChamadoSaida.de(
        servico.salvar_laudo(sessao, chamado_id, usuario, gestao=_eh_gestao(usuario), **dados.model_dump())
    )


@rotas.post("/chamados/{chamado_id}/pecas", response_model=ChamadoSaida, dependencies=[_pode(*TECNICA)])
def adicionar_peca(chamado_id: int, dados: PecaAdicionar, sessao: SessaoDep, usuario: UsuarioAtual):
    return ChamadoSaida.de(
        servico.adicionar_peca(
            sessao, chamado_id, usuario, gestao=_eh_gestao(usuario), peca_id=dados.peca_id, quantidade=dados.quantidade
        )
    )


@rotas.delete("/chamados/{chamado_id}/pecas/{item_id}", response_model=ChamadoSaida, dependencies=[_pode(*TECNICA)])
def remover_peca(chamado_id: int, item_id: int, sessao: SessaoDep, usuario: UsuarioAtual):
    return ChamadoSaida.de(servico.remover_peca(sessao, chamado_id, item_id, usuario, gestao=_eh_gestao(usuario)))


@rotas.post("/chamados/{chamado_id}/concluir", response_model=ChamadoSaida, dependencies=[_pode(*CONCLUIR)])
def concluir(chamado_id: int, dados: ChamadoConcluir, sessao: SessaoDep, usuario: UsuarioAtual):
    return ChamadoSaida.de(
        servico.concluir_chamado(sessao, chamado_id, usuario, gestao=_eh_gestao(usuario), **dados.model_dump())
    )


@rotas.post("/chamados/{chamado_id}/cancelar", response_model=ChamadoSaida, dependencies=[_pode(*GESTAO)])
def cancelar(chamado_id: int, dados: ChamadoCancelar, sessao: SessaoDep, usuario: UsuarioAtual):
    return ChamadoSaida.de(servico.cancelar_chamado(sessao, chamado_id, usuario, motivo=dados.motivo))


# ---------------------------------------------------------------- gestão


@rotas.get("/indicadores", dependencies=[_pode(*GESTAO)])
def obter_indicadores(sessao: SessaoDep, periodo_dias: int | None = Query(None, ge=1, le=3650), setor: str | None = None):
    return indicadores.indicadores(sessao, periodo_dias, setor)


@rotas.get("/graficos", dependencies=[_pode(*GESTAO)])
def obter_graficos(sessao: SessaoDep, periodo_dias: int | None = Query(None, ge=1, le=3650), setor: str | None = None):
    return indicadores.graficos(sessao, periodo_dias, setor)


@rotas.get("/auditoria", response_model=list[AuditoriaSaida], dependencies=[_pode(*GESTAO)])
def auditoria(sessao: SessaoDep, equipamento_id: int | None = None, limite: int = Query(100, ge=1, le=1000)):
    return [AuditoriaSaida.de(h) for h in servico.listar_auditoria(sessao, equipamento_id, limite)]
