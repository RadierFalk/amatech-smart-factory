"""Rotas do módulo de Rastreabilidade (/api/ras).

Permissões por persona. No sistema antigo quase tudo era liberado para qualquer usuário logado; aqui cada
ação ficou com quem faz esse trabalho na fábrica:

| Ação                                                   | Personas                                      |
|--------------------------------------------------------|-----------------------------------------------|
| Painel, produções, materiais, relatórios (consulta)    | todas com acesso ao módulo (rbac.py)          |
| Criar/editar produção, mudar etapa, não conformidade   | Operador, Inspetor, Supervisor, Administrador |
| Excluir produção                                       | Supervisor, Administrador                     |
| Solicitar material                                     | Operador, Almoxarife, Supervisor, Administrador |
| Baixa de material (estoque)                            | Almoxarife, Administrador (como no antigo)    |
| Componentes                                            | Almoxarife, Supervisor, Administrador         |
| Modelos e etapas                                       | Supervisor, Administrador                     |

A rota das máquinas (/api/ras/maquinas/status) não usa login: usa a chave X-API-Key (AMATECH_CHAVE_MAQUINAS).
"""
import secrets
from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select

from app.core.config import obter_configuracao
from app.core.deps import SessaoDep, UsuarioAtual, exigir_modulo, exigir_perfis
from app.core.rbac import Modulo, Perfil, tem_acesso
from app.modulos.auditoria.registro import definir_usuario
from app.modulos.rastreabilidade import cadastros, materiais, producao, relatorios
from app.modulos.rastreabilidade.constantes import ESTOQUE_CRITICO, StatusSolicitacao
from app.modulos.rastreabilidade.esquemas import (
    AvancarEtapa,
    BaixaCriar,
    BaixaEntrada,
    BaixaSaida,
    ComponenteAlterar,
    ComponenteCriar,
    ComponenteSaida,
    EtapaEntrada,
    EtapaSaida,
    MaquinaStatus,
    ModeloAlterar,
    ModeloCriar,
    ModeloSaida,
    NaoConformidadeEntrada,
    NaoConformidadeSaida,
    OpcoesSaida,
    PassagemSaida,
    PermissoesRas,
    ProducaoAlterar,
    ProducaoCriar,
    ProducaoDetalhe,
    ProducaoSaida,
    SolicitacaoAlterar,
    SolicitacaoCriar,
    SolicitacaoSaida,
)
from app.modulos.usuarios.modelos import Usuario

P = Perfil
PRODUCAO = (P.OPERADOR, P.INSPETOR, P.SUPERVISOR, P.ADMINISTRADOR)
GESTAO = (P.SUPERVISOR, P.ADMINISTRADOR)
SOLICITAR = (P.OPERADOR, P.ALMOXARIFE, P.SUPERVISOR, P.ADMINISTRADOR)
BAIXAR = (P.ALMOXARIFE, P.ADMINISTRADOR)
COMPONENTES = (P.ALMOXARIFE, P.SUPERVISOR, P.ADMINISTRADOR)


def _pode(*perfis: Perfil):
    return Depends(exigir_perfis(*perfis))


rotas = APIRouter(prefix="/api/ras", tags=["Rastreabilidade (RAS)"],
                  dependencies=[Depends(exigir_modulo(Modulo.RASTREABILIDADE))])


def _detalhe(sessao, p) -> ProducaoDetalhe:
    solicitacoes = materiais.listar_solicitacoes(sessao, producao_id=p.id)
    proxima = producao.proxima_etapa_sugerida(sessao, p)
    return ProducaoDetalhe(
        **ProducaoSaida.de(p).model_dump(),
        passagens=[PassagemSaida.de(h) for h in producao.passagens(sessao, p.id)],
        nao_conformidades=[NaoConformidadeSaida.de(n) for n in producao.nao_conformidades(sessao, p.id)],
        solicitacoes=[SolicitacaoSaida.de(s) for s in solicitacoes],
        materiais_pendentes=sum(1 for s in solicitacoes if s.status in ("PENDENTE", "PARCIAL")),
        mesmo_modelo=[ProducaoSaida.de(o) for o in producao.mesmo_modelo(sessao, p)],
        proxima_etapa_id=proxima.id if proxima else None,
    )


# ---------------------------------------------------------------- apoio


@rotas.get("/opcoes", response_model=OpcoesSaida)
def opcoes(sessao: SessaoDep, usuario: UsuarioAtual):
    perfil = Perfil(usuario.perfil)
    # Responsáveis possíveis: pessoas ativas com acesso ao módulo (sem contas de serviço).
    pessoas = sessao.scalars(select(Usuario).where(Usuario.ativo.is_(True)).order_by(Usuario.nome))
    return OpcoesSaida(
        etapas=[EtapaSaida.de(e) for e in cadastros.listar_etapas(sessao)],
        responsaveis=[{"id": u.id, "nome": u.nome, "matricula": u.matricula} for u in pessoas
                      if tem_acesso(u.perfil, Modulo.RASTREABILIDADE)],
        status_solicitacao=list(StatusSolicitacao),
        limite_estoque_critico=ESTOQUE_CRITICO,
        permissoes=PermissoesRas(
            producao=perfil in PRODUCAO, excluir_producao=perfil in GESTAO, solicitar=perfil in SOLICITAR,
            baixar=perfil in BAIXAR, componentes=perfil in COMPONENTES, modelos_etapas=perfil in GESTAO,
        ),
    )


@rotas.get("/painel")
def painel(sessao: SessaoDep):
    return relatorios.painel(sessao)


@rotas.get("/relatorios/{tipo}")
def relatorio(tipo: str, sessao: SessaoDep, de: date | None = None, ate: date | None = None):
    return relatorios.gerar(sessao, tipo, de, ate)


# ---------------------------------------------------------------- cadastros


@rotas.get("/etapas", response_model=list[EtapaSaida])
def listar_etapas(sessao: SessaoDep):
    return [EtapaSaida.de(e) for e in cadastros.listar_etapas(sessao)]


@rotas.post("/etapas", response_model=EtapaSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*GESTAO)])
def criar_etapa(dados: EtapaEntrada, sessao: SessaoDep):
    return EtapaSaida.de(cadastros.criar_etapa(sessao, **dados.model_dump()))


@rotas.put("/etapas/{etapa_id}", response_model=EtapaSaida, dependencies=[_pode(*GESTAO)])
def alterar_etapa(etapa_id: int, dados: EtapaEntrada, sessao: SessaoDep):
    return EtapaSaida.de(cadastros.alterar_etapa(sessao, etapa_id, **dados.model_dump()))


@rotas.delete("/etapas/{etapa_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_pode(*GESTAO)])
def excluir_etapa(etapa_id: int, sessao: SessaoDep):
    cadastros.excluir_etapa(sessao, etapa_id)


@rotas.get("/componentes", response_model=list[ComponenteSaida])
def listar_componentes(sessao: SessaoDep, incluir_inativos: bool = False):
    pendente = cadastros.pendente_por_componente(sessao)
    return [ComponenteSaida.de(c, pendente.get(c.id, 0)) for c in cadastros.listar_componentes(sessao, incluir_inativos)]


@rotas.post("/componentes", response_model=ComponenteSaida, status_code=status.HTTP_201_CREATED,
            dependencies=[_pode(*COMPONENTES)])
def criar_componente(dados: ComponenteCriar, sessao: SessaoDep):
    return ComponenteSaida.de(cadastros.criar_componente(sessao, **dados.model_dump()))


@rotas.patch("/componentes/{componente_id}", response_model=ComponenteSaida, dependencies=[_pode(*COMPONENTES)])
def alterar_componente(componente_id: int, dados: ComponenteAlterar, sessao: SessaoDep):
    c = cadastros.alterar_componente(sessao, componente_id, **dados.model_dump(exclude_unset=True))
    return ComponenteSaida.de(c, cadastros.pendente_por_componente(sessao).get(c.id, 0))


@rotas.get("/modelos", response_model=list[ModeloSaida])
def listar_modelos(sessao: SessaoDep, incluir_inativos: bool = False):
    contagem = cadastros.producoes_por_modelo(sessao)
    return [ModeloSaida.de(m, contagem.get(m.id, 0)) for m in cadastros.listar_modelos(sessao, incluir_inativos)]


@rotas.post("/modelos", response_model=ModeloSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*GESTAO)])
def criar_modelo(dados: ModeloCriar, sessao: SessaoDep):
    m = cadastros.criar_modelo(sessao, codigo=dados.codigo, nome=dados.nome, meta=dados.meta, componentes=dados.lista())
    return ModeloSaida.de(m)


@rotas.patch("/modelos/{modelo_id}", response_model=ModeloSaida, dependencies=[_pode(*GESTAO)])
def alterar_modelo(modelo_id: int, dados: ModeloAlterar, sessao: SessaoDep):
    valores = dados.model_dump(exclude_unset=True, exclude={"componentes"})
    lista = [(i.componente_id, i.quantidade) for i in dados.componentes] if dados.componentes is not None else None
    m = cadastros.alterar_modelo(sessao, modelo_id, componentes=lista, **valores)
    return ModeloSaida.de(m, cadastros.producoes_por_modelo(sessao).get(m.id, 0))


# ---------------------------------------------------------------- produções


@rotas.get("/producoes", response_model=list[ProducaoSaida])
def listar_producoes(
    sessao: SessaoDep,
    busca: str | None = None,
    etapa_id: int | None = None,
    modelo_id: int | None = None,
    limite: int = Query(500, ge=1, le=2000),
):
    return [ProducaoSaida.de(p) for p in producao.listar(sessao, busca=busca, etapa_id=etapa_id, modelo_id=modelo_id, limite=limite)]


@rotas.get("/producoes/{producao_id}", response_model=ProducaoDetalhe)
def obter_producao(producao_id: int, sessao: SessaoDep):
    return _detalhe(sessao, producao.obter(sessao, producao_id))


@rotas.post("/producoes", response_model=ProducaoDetalhe, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*PRODUCAO)])
def criar_producao(dados: ProducaoCriar, sessao: SessaoDep, usuario: UsuarioAtual):
    return _detalhe(sessao, producao.criar(sessao, usuario, **dados.model_dump()))


@rotas.put("/producoes/{producao_id}", response_model=ProducaoDetalhe, dependencies=[_pode(*PRODUCAO)])
def alterar_producao(producao_id: int, dados: ProducaoAlterar, sessao: SessaoDep):
    return _detalhe(sessao, producao.alterar(sessao, producao_id, **dados.model_dump()))


@rotas.delete("/producoes/{producao_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_pode(*GESTAO)])
def excluir_producao(producao_id: int, sessao: SessaoDep):
    producao.excluir(sessao, producao_id)


@rotas.post("/producoes/{producao_id}/etapa", response_model=ProducaoDetalhe, dependencies=[_pode(*PRODUCAO)])
def avancar_etapa(producao_id: int, dados: AvancarEtapa, sessao: SessaoDep, usuario: UsuarioAtual):
    return _detalhe(sessao, producao.avancar_etapa(sessao, producao_id, usuario, **dados.model_dump()))


@rotas.post("/producoes/{producao_id}/nao-conformidades", response_model=ProducaoDetalhe,
            status_code=status.HTTP_201_CREATED, dependencies=[_pode(*PRODUCAO)])
def registrar_nao_conformidade(producao_id: int, dados: NaoConformidadeEntrada, sessao: SessaoDep, usuario: UsuarioAtual):
    producao.registrar_nao_conformidade(sessao, producao_id, usuario, **dados.model_dump())
    return _detalhe(sessao, producao.obter(sessao, producao_id))


@rotas.post("/producoes/{producao_id}/solicitar-materiais", dependencies=[_pode(*SOLICITAR)])
def solicitar_materiais(producao_id: int, sessao: SessaoDep, usuario: UsuarioAtual):
    """Cria uma solicitação por componente da lista do modelo (sem repetir os que já têm solicitação ativa)."""
    return materiais.solicitar_lista_do_modelo(sessao, usuario, producao_id)


# ---------------------------------------------------------------- materiais


@rotas.get("/solicitacoes", response_model=list[SolicitacaoSaida])
def listar_solicitacoes(sessao: SessaoDep, status_solicitacao: StatusSolicitacao | None = Query(None, alias="status"),
                        producao_id: int | None = None):
    return [SolicitacaoSaida.de(s) for s in materiais.listar_solicitacoes(sessao, status_solicitacao, producao_id)]


@rotas.post("/solicitacoes", response_model=SolicitacaoSaida, status_code=status.HTTP_201_CREATED,
            dependencies=[_pode(*SOLICITAR)])
def criar_solicitacao(dados: SolicitacaoCriar, sessao: SessaoDep, usuario: UsuarioAtual):
    return SolicitacaoSaida.de(materiais.criar_solicitacao(sessao, usuario, **dados.model_dump()))


@rotas.put("/solicitacoes/{solicitacao_id}", response_model=SolicitacaoSaida, dependencies=[_pode(*SOLICITAR)])
def alterar_solicitacao(solicitacao_id: int, dados: SolicitacaoAlterar, sessao: SessaoDep):
    return SolicitacaoSaida.de(materiais.alterar_solicitacao(sessao, solicitacao_id, **dados.model_dump()))


@rotas.delete("/solicitacoes/{solicitacao_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_pode(*SOLICITAR)])
def excluir_solicitacao(solicitacao_id: int, sessao: SessaoDep):
    materiais.excluir_solicitacao(sessao, solicitacao_id)


@rotas.get("/baixas", response_model=list[BaixaSaida])
def listar_baixas(sessao: SessaoDep):
    return [BaixaSaida.de(b) for b in materiais.listar_baixas(sessao)]


@rotas.post("/baixas", response_model=BaixaSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*BAIXAR)])
def criar_baixa(dados: BaixaCriar, sessao: SessaoDep, usuario: UsuarioAtual):
    return BaixaSaida.de(materiais.criar_baixa(sessao, usuario, **dados.model_dump()))


@rotas.put("/baixas/{baixa_id}", response_model=BaixaSaida, dependencies=[_pode(*BAIXAR)])
def alterar_baixa(baixa_id: int, dados: BaixaEntrada, sessao: SessaoDep):
    return BaixaSaida.de(materiais.alterar_baixa(sessao, baixa_id, **dados.model_dump()))


@rotas.delete("/baixas/{baixa_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_pode(*BAIXAR)])
def excluir_baixa(baixa_id: int, sessao: SessaoDep):
    materiais.excluir_baixa(sessao, baixa_id)


# ---------------------------------------------------------------- máquinas (sem login, com chave)

rotas_maquinas = APIRouter(prefix="/api/ras/maquinas", tags=["Rastreabilidade (RAS)"])


@rotas_maquinas.post("/status")
def status_por_maquina(dados: MaquinaStatus, sessao: SessaoDep, x_api_key: str | None = Header(None)):
    """RF017: a máquina informa a etapa do notebook pelo número de série. Repetir a mesma etapa não grava nada."""
    cfg = obter_configuracao()
    if not x_api_key or not secrets.compare_digest(x_api_key, cfg.chave_maquinas):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave de API inválida.")
    servico = sessao.scalar(select(Usuario).where(Usuario.matricula == cfg.matricula_servico))
    if servico is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            f"Usuário de serviço {cfg.matricula_servico} não cadastrado (rode o seed_demo ou a migração).")
    definir_usuario(sessao, servico)  # auditoria em nome da conta de serviço
    p, alterado = producao.atualizar_por_maquina(
        sessao, servico, numero_serie=dados.numero_serie, etapa_nome=dados.etapa, maquina=dados.maquina
    )
    return {"alterado": alterado, "producao": ProducaoSaida.de(p)}
