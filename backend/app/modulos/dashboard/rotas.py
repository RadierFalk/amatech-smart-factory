"""Rotas do Dashboard (/api/dsh).

Permissões (no sistema antigo: Supervisor lançava metas e perdas, importava planilhas e ajustava os limites;
Gestor/Diretoria e os demais só consultavam):

| Ação                                                  | Personas                                  |
|-------------------------------------------------------|-------------------------------------------|
| Painel e histórico                                    | todas com acesso ao módulo (rbac.py)      |
| Metas, perdas e importação de planilhas               | Supervisor, Administrador                 |
| Turnos, tipos de perda e limites do semáforo          | Supervisor, Administrador                 |
"""
from datetime import date

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy import select

from app.core.deps import SessaoDep, UsuarioAtual, exigir_modulo, exigir_perfis
from app.core.rbac import Modulo, Perfil
from app.modulos.dashboard import cadastros, calculo
from app.modulos.dashboard.constantes import Indicador
from app.modulos.dashboard.esquemas import (
    ImportacaoEntrada,
    ImportacaoSaida,
    LimiteEntrada,
    LimiteSaida,
    MetaEntrada,
    MetaSaida,
    OpcoesSaida,
    PerdaEntrada,
    PerdaSaida,
    PermissoesDsh,
    TipoPerdaAlterar,
    TipoPerdaCriar,
    TipoPerdaSaida,
    TurnoEntrada,
    TurnoSaida,
)
from app.modulos.dashboard.modelos import Limite
from app.modulos.qualidade.modelos import Estacao
from app.modulos.rastreabilidade.modelos import Modelo

GESTAO = (Perfil.SUPERVISOR, Perfil.ADMINISTRADOR)
_gestao = Depends(exigir_perfis(*GESTAO))

rotas = APIRouter(prefix="/api/dsh", tags=["Dashboard (DSH)"], dependencies=[Depends(exigir_modulo(Modulo.DASHBOARD))])


def _filtro(de: date | None, ate: date | None, turno_id: int | None, modelo_id: int | None) -> calculo.Filtro:
    hoje = calculo.hoje_na_fabrica()
    return calculo.Filtro(de=de or ate or hoje, ate=ate or de or hoje, turno_id=turno_id, modelo_id=modelo_id)


@rotas.get("/opcoes", response_model=OpcoesSaida)
def opcoes(sessao: SessaoDep, usuario: UsuarioAtual):
    gestao = Perfil(usuario.perfil) in GESTAO
    return OpcoesSaida(
        turnos=[TurnoSaida.de(t) for t in cadastros.listar_turnos(sessao)],
        modelos=[{"id": m.id, "nome": m.nome, "codigo": m.codigo}
                 for m in sessao.scalars(select(Modelo).where(Modelo.ativo.is_(True)).order_by(Modelo.nome))],
        estacoes=[{"id": e.id, "nome": e.nome}
                  for e in sessao.scalars(select(Estacao).where(Estacao.ativo.is_(True)).order_by(Estacao.nome))],
        tipos_perda=[TipoPerdaSaida.de(t) for t in cadastros.listar_tipos_perda(sessao, incluir_inativos=gestao)],
        limites=[LimiteSaida.de(l) for l in sessao.scalars(select(Limite).order_by(Limite.indicador))],
        hoje=calculo.hoje_na_fabrica(),
        permissoes=PermissoesDsh(lancar=gestao, configurar=gestao),
    )


@rotas.get("/painel")
def painel(sessao: SessaoDep, de: date | None = None, ate: date | None = None, turno_id: int | None = None,
           modelo_id: int | None = None):
    """Os seis indicadores do período, com o semáforo, os dados dos gráficos e as máquinas paradas agora.
    Sem datas: hoje (dia da fábrica)."""
    return calculo.painel(sessao, _filtro(de, ate, turno_id, modelo_id))


@rotas.get("/historico/producao")
def historico_producao(sessao: SessaoDep, de: date | None = None, ate: date | None = None, turno_id: int | None = None,
                       modelo_id: int | None = None):
    return calculo.historico_producao(sessao, _filtro(de, ate, turno_id, modelo_id))


# ---------------------------------------------------------------- metas


@rotas.get("/metas", response_model=list[MetaSaida])
def listar_metas(sessao: SessaoDep, de: date | None = None, ate: date | None = None):
    f = _filtro(de, ate, None, None)
    f.validar()
    return [MetaSaida.de(m) for m in cadastros.listar_metas(sessao, f.de, f.ate)]


@rotas.put("/metas", response_model=MetaSaida, dependencies=[_gestao])
def gravar_meta(dados: MetaEntrada, sessao: SessaoDep, usuario: UsuarioAtual):
    """Cria ou atualiza a meta do dia + turno + modelo (RN09)."""
    return MetaSaida.de(cadastros.gravar_meta(sessao, usuario, **dados.model_dump()))


@rotas.delete("/metas/{meta_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_gestao])
def excluir_meta(meta_id: int, sessao: SessaoDep):
    cadastros.excluir_meta(sessao, meta_id)


# ---------------------------------------------------------------- perdas


@rotas.get("/perdas", response_model=list[PerdaSaida])
def listar_perdas(sessao: SessaoDep, de: date | None = None, ate: date | None = None, turno_id: int | None = None,
                  modelo_id: int | None = None):
    f = _filtro(de, ate, turno_id, modelo_id)
    f.validar()
    return [PerdaSaida.de(p) for p in calculo.perdas(sessao, f)]


@rotas.post("/perdas", response_model=PerdaSaida, status_code=status.HTTP_201_CREATED, dependencies=[_gestao])
def registrar_perda(dados: PerdaEntrada, sessao: SessaoDep, usuario: UsuarioAtual):
    return PerdaSaida.de(cadastros.registrar_perda(sessao, usuario, **dados.model_dump()))


@rotas.delete("/perdas/{perda_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_gestao])
def excluir_perda(perda_id: int, sessao: SessaoDep):
    cadastros.excluir_perda(sessao, perda_id)


# ---------------------------------------------------------------- planilhas


@rotas.get("/importacao/{tipo}/modelo")
def baixar_modelo(tipo: str):
    return Response(cadastros.modelo_csv(tipo), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="modelo_{tipo}.csv"'})


@rotas.post("/importacao/{tipo}", response_model=ImportacaoSaida, dependencies=[_gestao])
def importar(tipo: str, dados: ImportacaoEntrada, sessao: SessaoDep, usuario: UsuarioAtual):
    """Tudo ou nada (RN06): com qualquer erro nada é gravado, e a resposta lista linha, coluna e problema."""
    r = cadastros.importar_csv(sessao, usuario, tipo, dados.conteudo)
    return ImportacaoSaida(linhas_lidas=r.linhas_lidas, importadas=r.importadas,
                           erros=[e.__dict__ for e in r.erros])


# ---------------------------------------------------------------- configuração


@rotas.put("/turnos/{turno_id}", response_model=TurnoSaida, dependencies=[_gestao])
def alterar_turno(turno_id: int, dados: TurnoEntrada, sessao: SessaoDep):
    return TurnoSaida.de(cadastros.alterar_turno(sessao, turno_id, **dados.model_dump()))


@rotas.post("/tipos-perda", response_model=TipoPerdaSaida, status_code=status.HTTP_201_CREATED, dependencies=[_gestao])
def criar_tipo_perda(dados: TipoPerdaCriar, sessao: SessaoDep):
    return TipoPerdaSaida.de(cadastros.criar_tipo_perda(sessao, nome=dados.nome))


@rotas.patch("/tipos-perda/{tipo_id}", response_model=TipoPerdaSaida, dependencies=[_gestao])
def alterar_tipo_perda(tipo_id: int, dados: TipoPerdaAlterar, sessao: SessaoDep):
    return TipoPerdaSaida.de(cadastros.alterar_tipo_perda(sessao, tipo_id, ativo=dados.ativo))


@rotas.put("/limites/{indicador}", response_model=LimiteSaida, dependencies=[_gestao])
def salvar_limites(indicador: Indicador, dados: LimiteEntrada, sessao: SessaoDep):
    return LimiteSaida.de(cadastros.salvar_limites(sessao, indicador, **dados.model_dump()))

