"""
Matriz de Perfis (Personas) e Permissões do ERP AMATECH.
Controla rigorosamente quais módulos cada persona tem poder para acessar e operar.

Regra Central:
Cada tipo de usuário só visualiza e acessa os módulos onde possui atribuições.
"""
from dataclasses import dataclass
from typing import Any

from config import DASHBOARD_URL, MANUTENCAO_URL, QUALIDADE_URL, RASTREABILIDADE_URL

# ============================================================
# PERSONAS CANÔNICAS DO ERP
# ============================================================

ADMINISTRADOR = "Administrador"
INSPETOR = "Inspetor de Qualidade"
OPERADOR = "Operador de Produção"
TECNICO = "Técnico de Manutenção"
ALMOXARIFE = "Almoxarife"

PERFIS_TODOS = [
    ADMINISTRADOR,
    INSPETOR,
    OPERADOR,
    TECNICO,
    ALMOXARIFE,
]

PREFIXOS_MATRICULA = {
    ADMINISTRADOR: "ADM",
    INSPETOR: "QUA",
    OPERADOR: "OPE",
    TECNICO: "TEC",
    ALMOXARIFE: "ALM",
}

DESCRICAO_PERSONAS = {
    ADMINISTRADOR: "Gestão executiva fabril, segurança corporativa, auditoria e controle total dos módulos e usuários.",
    INSPETOR: "Inspeção técnica de qualidade, testes funcionais, registro de não-conformidades e travamento de lotes.",
    OPERADOR: "Chão de fábrica, montagem seriada, leitura de séries, reporte de falhas e abertura de chamados.",
    TECNICO: "Manutenção eletromecânica preventiva e corretiva, emissão/fechamento de O.S. e reposição de peças.",
    ALMOXARIFE: "Gestão de inventário, fluxo de materiais (BOM), conferência de suprimentos e baixa de insumos.",
}

# ============================================================
# IDENTIFICADORES DOS MÓDULOS
# ============================================================

MODULO_RASTREABILIDADE = "rastreabilidade"
MODULO_QUALIDADE = "qualidade"
MODULO_MANUTENCAO = "manutencao"
MODULO_USUARIOS = "usuarios"


@dataclass(frozen=True)
class ModuloERP:
    id: str
    nome: str
    sigla: str
    icone: str
    descricao: str
    url: str
    categoria: str
    perfis_permitidos: frozenset[str]
    poder_do_perfil: dict[str, str]


# Catálogo dos 4 módulos fundamentais do ERP
CATALOGO_MODULOS: dict[str, ModuloERP] = {
    MODULO_RASTREABILIDADE: ModuloERP(
        id=MODULO_RASTREABILIDADE,
        nome="Rastreabilidade e Materiais",
        sigla="RAS",
        icone=":material/qr_code_2:",
        descricao="Acompanhamento individual de produtos por número de série, fluxo de montagem em linha, controle de lotes e estoque de componentes (BOM).",
        url=RASTREABILIDADE_URL,
        categoria="Manufatura",
        perfis_permitidos=frozenset({ADMINISTRADOR, OPERADOR, INSPETOR, ALMOXARIFE}),
        poder_do_perfil={
            ADMINISTRADOR: "Acesso administrativo completo, cadastro de produtos, regras de fluxo e relatórios executivos.",
            OPERADOR: "Leitura de número de série e apontamento de avanço nas etapas de produção da linha.",
            INSPETOR: "Consulta de histórico de fabricação e rastreabilidade da unidade inspecionada.",
            ALMOXARIFE: "Recebimento de materiais, baixa manual de estoque e monitoramento de itens críticos.",
        },
    ),
    MODULO_QUALIDADE: ModuloERP(
        id=MODULO_QUALIDADE,
        nome="Controle da Qualidade e Defeitos",
        sigla="QLD",
        icone=":material/verified:",
        descricao="Registro e tratamento de não conformidades, estatística de falhas por posto, reprovação técnica e acionamento automático da manutenção.",
        url=QUALIDADE_URL,
        categoria="Qualidade",
        perfis_permitidos=frozenset({ADMINISTRADOR, INSPETOR, OPERADOR, ALMOXARIFE}),
        poder_do_perfil={
            ADMINISTRADOR: "Acesso integral a ocorrências, indicadores de qualidade, ocultação e auditoria.",
            INSPETOR: "Registro de defeitos, alteração de status de produto (Reprovado/Reprocesso) e abertura de chamados técnicos.",
            OPERADOR: "Apontamento de defeitos observados no posto de trabalho e abertura de chamados emergenciais.",
            ALMOXARIFE: "Consulta a ocorrências e histórico de peças reprovadas para controle de lotes defeituosos.",
        },
    ),
    MODULO_MANUTENCAO: ModuloERP(
        id=MODULO_MANUTENCAO,
        nome="Gestão da Manutenção de Ativos",
        sigla="MNT",
        icone=":material/build:",
        descricao="Monitoramento do parque fabril (TAGs), atendimento a chamados de quebra, Ordens de Serviço (OS), manutenções preventivas e controle de peças.",
        url=MANUTENCAO_URL,
        categoria="Engenharia Fabril",
        perfis_permitidos=frozenset({ADMINISTRADOR, TECNICO, OPERADOR}),
        poder_do_perfil={
            ADMINISTRADOR: "Visão executiva, cadastro de equipamentos/peças, aprovação de OS e métricas globais de MTTR/MTBF.",
            TECNICO: "Fila de chamados técnicos, execução de corretivas/preventivas, diagnóstico e substituição de insumos.",
            OPERADOR: "Visualização do painel de disponibilidade de máquinas e abertura de chamados corretivos por quebra.",
        },
    ),
    MODULO_USUARIOS: ModuloERP(
        id=MODULO_USUARIOS,
        nome="Gestão de Usuários e Acessos",
        sigla="IAM",
        icone=":material/manage_accounts:",
        descricao="Administração corporativa do ERP: emissão de matrículas funcionais, concessão de personas, ativação/bloqueio e redefinição de senhas.",
        url="#usuarios",
        categoria="Administração Central",
        perfis_permitidos=frozenset({ADMINISTRADOR}),
        poder_do_perfil={
            ADMINISTRADOR: "Gestão completa de identidades corporativas, papéis e privilégios de acesso aos módulos.",
        },
    ),
}


# ============================================================
# FUNÇÕES DE CONSULTA RBAC
# ============================================================

def obter_perfil_usuario(usuario: dict[str, Any] | None) -> str | None:
    """Extrai o perfil/persona do dicionário de usuário da sessão."""
    if not usuario:
        return None
    return usuario.get("perfil")


def tem_acesso_modulo(usuario: dict[str, Any] | None, id_modulo: str) -> bool:
    """Verifica se o usuário autenticado possui poder de acesso ao módulo informado."""
    perfil = obter_perfil_usuario(usuario)
    if not perfil:
        return False
    modulo = CATALOGO_MODULOS.get(id_modulo)
    if not modulo:
        return False
    return perfil in modulo.perfis_permitidos


def modulos_permitidos(usuario: dict[str, Any] | None) -> list[ModuloERP]:
    """Retorna estritamente os módulos que a persona do usuário tem permissão para visualizar e utilizar."""
    perfil = obter_perfil_usuario(usuario)
    if not perfil:
        return []
    return [
        modulo for modulo in CATALOGO_MODULOS.values()
        if perfil in modulo.perfis_permitidos
    ]


def obter_papel_no_modulo(usuario: dict[str, Any] | None, id_modulo: str) -> str:
    """Retorna o escopo de atuação do usuário dentro do módulo especificado."""
    perfil = obter_perfil_usuario(usuario)
    if not perfil:
        return "Sem permissão"
    modulo = CATALOGO_MODULOS.get(id_modulo)
    if not modulo:
        return "Módulo inexistente"
    return modulo.poder_do_perfil.get(perfil, "Sem atribuição específica")
