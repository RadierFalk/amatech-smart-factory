"""Rotas do módulo de Qualidade (/api/qld).

Permissões por persona (matriz de qualidade/permissoes.py; o Supervisor não existia lá e ganhou
as mesmas permissões do Inspetor, porque o GES-0001 era Administrador no banco antigo da Qualidade):

| Ação                                                    | Personas                                         |
|---------------------------------------------------------|--------------------------------------------------|
| Painel, histórico, consulta                             | todas com acesso ao módulo (rbac.py)             |
| Registrar e editar ocorrência, abrir chamado na MNT     | Operador, Inspetor, Supervisor, Administrador    |
| Ocultar ocorrência                                      | Inspetor, Supervisor, Administrador              |
| Cadastros (estações, tipos de defeito)                  | Supervisor, Administrador                        |

Notebooks: vêm da Rastreabilidade (GET /notebooks). A lista de produtos (GET /produtos) é só consulta: os espelhos
das produções e o histórico do sistema antigo.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import SessaoDep, UsuarioAtual, exigir_modulo, exigir_perfis
from app.core.rbac import Modulo, Perfil
from app.modulos.qualidade import indicadores, servico
from app.modulos.qualidade.constantes import (
    ROTULOS_CLASSIFICACAO,
    ROTULOS_SITUACAO,
    ROTULOS_STATUS,
    Classificacao,
    SituacaoProduto,
    StatusOcorrencia,
)
from app.modulos.qualidade.esquemas import (
    AvisoSaida,
    ItemAlterar,
    ItemCriar,
    ItemSaida,
    MaquinaSaida,
    NotebookSaida,
    OcorrenciaEntrada,
    OcorrenciaRegistrar,
    OcorrenciaSaida,
    OpcoesSaida,
    PermissoesQld,
    ProdutoSaida,
    RegistroSaida,
)
from app.modulos.qualidade.modelos import Ocorrencia

P = Perfil
REGISTRAR = (P.OPERADOR, P.INSPETOR, P.SUPERVISOR, P.ADMINISTRADOR)
OCULTAR = (P.INSPETOR, P.SUPERVISOR, P.ADMINISTRADOR)
CADASTROS = (P.SUPERVISOR, P.ADMINISTRADOR)


def _pode(*perfis: Perfil):
    return Depends(exigir_perfis(*perfis))


rotas = APIRouter(prefix="/api/qld", tags=["Qualidade (QLD)"], dependencies=[Depends(exigir_modulo(Modulo.QUALIDADE))])


def _saida(sessao, ocorrencias: list[Ocorrencia]) -> list[OcorrenciaSaida]:
    chamados = servico.chamados_das_ocorrencias(sessao, [o.id for o in ocorrencias])
    return [OcorrenciaSaida.de(o, chamados.get(o.id)) for o in ocorrencias]


# ---------------------------------------------------------------- apoio


@rotas.get("/opcoes", response_model=OpcoesSaida)
def opcoes(usuario: UsuarioAtual):
    perfil = Perfil(usuario.perfil)
    return OpcoesSaida(
        classificacoes={k.value: v for k, v in ROTULOS_CLASSIFICACAO.items()},
        situacoes={k.value: v for k, v in ROTULOS_SITUACAO.items()},
        status={k.value: v for k, v in ROTULOS_STATUS.items()},
        permissoes=PermissoesQld(
            registrar=perfil in REGISTRAR,
            editar=perfil in REGISTRAR,
            ocultar=perfil in OCULTAR,
            abrir_chamado=perfil in REGISTRAR,
            cadastros=perfil in CADASTROS,
        ),
    )


@rotas.get("/maquinas", response_model=list[MaquinaSaida])
def maquinas(sessao: SessaoDep):
    return [MaquinaSaida.de(e) for e in servico.listar_maquinas(sessao)]


# ---------------------------------------------------------------- cadastros


@rotas.get("/notebooks", response_model=list[NotebookSaida])
def listar_notebooks(sessao: SessaoDep, busca: str | None = None, limite: int = Query(50, ge=1, le=200)):
    """Produções da Rastreabilidade ainda não expedidas, para escolher o notebook da ocorrência."""
    return [NotebookSaida.de(p) for p in servico.listar_notebooks(sessao, busca, limite)]


@rotas.get("/produtos", response_model=list[ProdutoSaida])
def listar_produtos(sessao: SessaoDep, incluir_inativos: bool = False):
    """Notebooks que já têm ocorrência (espelhos das produções) e os do histórico. Só consulta."""
    return [ProdutoSaida.de(p) for p in servico.listar_cadastro(sessao, "produto", incluir_inativos)]


@rotas.get("/estacoes", response_model=list[ItemSaida])
def listar_estacoes(sessao: SessaoDep, incluir_inativos: bool = False):
    return [ItemSaida.de(i) for i in servico.listar_cadastro(sessao, "estacao", incluir_inativos)]


@rotas.post("/estacoes", response_model=ItemSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*CADASTROS)])
def criar_estacao(dados: ItemCriar, sessao: SessaoDep):
    return ItemSaida.de(servico.criar_cadastro(sessao, "estacao", **dados.model_dump()))


@rotas.patch("/estacoes/{item_id}", response_model=ItemSaida, dependencies=[_pode(*CADASTROS)])
def alterar_estacao(item_id: int, dados: ItemAlterar, sessao: SessaoDep):
    return ItemSaida.de(servico.alterar_cadastro(sessao, "estacao", item_id, **dados.model_dump(exclude_unset=True)))


@rotas.get("/tipos-defeito", response_model=list[ItemSaida])
def listar_tipos(sessao: SessaoDep, incluir_inativos: bool = False):
    return [ItemSaida.de(i) for i in servico.listar_cadastro(sessao, "tipo_defeito", incluir_inativos)]


@rotas.post("/tipos-defeito", response_model=ItemSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*CADASTROS)])
def criar_tipo(dados: ItemCriar, sessao: SessaoDep):
    return ItemSaida.de(servico.criar_cadastro(sessao, "tipo_defeito", **dados.model_dump()))


@rotas.patch("/tipos-defeito/{item_id}", response_model=ItemSaida, dependencies=[_pode(*CADASTROS)])
def alterar_tipo(item_id: int, dados: ItemAlterar, sessao: SessaoDep):
    return ItemSaida.de(servico.alterar_cadastro(sessao, "tipo_defeito", item_id, **dados.model_dump(exclude_unset=True)))


# ---------------------------------------------------------------- ocorrências


@rotas.get("/ocorrencias", response_model=list[OcorrenciaSaida])
def listar_ocorrencias(
    sessao: SessaoDep,
    busca: str | None = None,
    classificacao: Classificacao | None = None,
    situacao: SituacaoProduto | None = None,
    status_ocorrencia: StatusOcorrencia | None = Query(None, alias="status"),
    estacao_id: int | None = None,
    tipo_defeito_id: int | None = None,
    equipamento_id: int | None = None,
    de: date | None = None,
    ate: date | None = None,
    limite: int = Query(500, ge=1, le=2000),
):
    ocorrencias = servico.listar(
        sessao, busca=busca, classificacao=classificacao, situacao=situacao, status=status_ocorrencia,
        estacao_id=estacao_id, tipo_defeito_id=tipo_defeito_id, equipamento_id=equipamento_id, de=de, ate=ate, limite=limite,
    )
    return _saida(sessao, ocorrencias)


@rotas.get("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaSaida)
def obter_ocorrencia(ocorrencia_id: int, sessao: SessaoDep):
    return _saida(sessao, [servico.obter(sessao, ocorrencia_id)])[0]


@rotas.post("/ocorrencias", response_model=RegistroSaida, status_code=status.HTTP_201_CREATED, dependencies=[_pode(*REGISTRAR)])
def registrar_ocorrencia(dados: OcorrenciaRegistrar, sessao: SessaoDep, usuario: UsuarioAtual):
    """Registra a ocorrência. Com `abrir_chamado`, abre chamado na Manutenção; a recusa dela vira aviso."""
    oc, avisos = servico.registrar(sessao, usuario, dados.dados(), abrir_chamado=dados.abrir_chamado)
    return RegistroSaida(ocorrencia=_saida(sessao, [oc])[0], avisos=[AvisoSaida.de(a) for a in avisos])


@rotas.put("/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaSaida, dependencies=[_pode(*REGISTRAR)])
def editar_ocorrencia(ocorrencia_id: int, dados: OcorrenciaEntrada, sessao: SessaoDep):
    return _saida(sessao, [servico.editar(sessao, ocorrencia_id, dados.dados())])[0]


@rotas.post("/ocorrencias/{ocorrencia_id}/ocultar", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_pode(*OCULTAR)])
def ocultar_ocorrencia(ocorrencia_id: int, sessao: SessaoDep):
    servico.ocultar(sessao, ocorrencia_id)


@rotas.post("/ocorrencias/{ocorrencia_id}/chamado", response_model=RegistroSaida, dependencies=[_pode(*REGISTRAR)])
def abrir_chamado(ocorrencia_id: int, sessao: SessaoDep, usuario: UsuarioAtual):
    """Abre o chamado na Manutenção depois do registro (ex.: a máquina estava com outra OS ativa)."""
    oc = servico.obter(sessao, ocorrencia_id)
    aviso = servico.abrir_chamado_manutencao(sessao, oc, usuario)
    return RegistroSaida(ocorrencia=_saida(sessao, [oc])[0], avisos=[AvisoSaida.de(aviso)])


# ---------------------------------------------------------------- painel


@rotas.get("/indicadores")
def obter_indicadores(sessao: SessaoDep, de: date | None = None, ate: date | None = None):
    return indicadores.indicadores(sessao, de, ate)
