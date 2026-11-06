"""
Matriz de Perfis (Personas) e Permissões do ERP AMATECH.
Controla rigorosamente quais módulos e funcionalidades cada persona tem poder para acessar e operar.

Regra Central:
Cada tipo de usuário só visualiza e acessa os módulos onde possui atribuições.
Toda a navegação ocorre de forma integrada dentro do próprio sistema (mesma sessão e porta).
"""
from dataclasses import dataclass

# ============================================================
# PERSONAS CANÔNICAS DO ERP UNIFICADO (6 PERFIS)
# ============================================================

ADMINISTRADOR = "Administrador"
SUPERVISOR = "Supervisor / Gestor"
INSPETOR = "Inspetor de Qualidade"
OPERADOR = "Operador de Produção"
TECNICO = "Técnico de Manutenção"
ALMOXARIFE = "Almoxarife"

PERFIS_TODOS = [
    ADMINISTRADOR,
    SUPERVISOR,
    INSPETOR,
    OPERADOR,
    TECNICO,
    ALMOXARIFE,
]

PREFIXOS_MATRICULA = {
    ADMINISTRADOR: "ADM",
    SUPERVISOR: "GES",
    INSPETOR: "QUA",
    OPERADOR: "OPE",
    TECNICO: "TEC",
    ALMOXARIFE: "ALM",
}

DESCRICAO_PERSONAS = {
    ADMINISTRADOR: "Gestão executiva e administração global do ERP: acesso total aos 5 módulos, cadastros mestres e controle de usuários.",
    SUPERVISOR: "Supervisão e gerência industrial: indicadores de OEE/metas, painel consolidado, aprovação de O.S., sincronização entre setores e relatórios.",
    INSPETOR: "Inspeção técnica de qualidade: registro/edição/ocultação de não-conformidades, retrabalho, rastreabilidade de séries e acionamento de manutenção.",
    OPERADOR: "Operação de chão de fábrica: leitura de número de série, avanço de etapas na linha, registro de produção/defeitos e abertura de chamados.",
    TECNICO: "Manutenção eletromecânica preventiva e corretiva: fila de chamados, execução de Ordens de Serviço (O.S.), apontamento de paradas e peças.",
    ALMOXARIFE: "Logística interna e almoxarifado: gestão de componentes (BOM), atendimento de solicitações de materiais, baixas de estoque e consulta de qualidade.",
}

# ============================================================
# IDENTIFICADORES DOS 5 MÓDULOS INTEGRADOS DO ERP
# ============================================================

MODULO_RASTREABILIDADE = "rastreabilidade"
MODULO_QUALIDADE = "qualidade"
MODULO_MANUTENCAO = "manutencao"
MODULO_DASHBOARD = "dashboard"
MODULO_USUARIOS = "usuarios"


@dataclass(frozen=True)
class ModuloERP:
    id: str
    nome: str
    sigla: str
    icone: str
    descricao: str
    categoria: str
    perfis_permitidos: frozenset[str]
    poder_do_perfil: dict[str, str]
    url: str = ""


# Catálogo dos 5 módulos integrados do ERP AMATECH
CATALOGO_MODULOS: dict[str, ModuloERP] = {
    MODULO_RASTREABILIDADE: ModuloERP(
        id=MODULO_RASTREABILIDADE,
        nome="Rastreabilidade e Materiais",
        sigla="RAS",
        icone=":material/qr_code_2:",
        descricao="Acompanhamento individual de notebooks por número de série, fluxo de passagem nas estações, solicitações de material e baixas de estoque (BOM).",
        categoria="Manufatura & Logística",
        perfis_permitidos=frozenset({ADMINISTRADOR, SUPERVISOR, OPERADOR, INSPETOR, ALMOXARIFE}),
        poder_do_perfil={
            ADMINISTRADOR: "Acesso total: terminal, produções, solicitações, baixas de estoque, cadastros de produtos/componentes (BOM), etapas e relatórios.",
            SUPERVISOR: "Acompanhamento de linha: terminal, rastreamento de produções, solicitações de materiais e emissão de relatórios.",
            OPERADOR: "Operação de linha: terminal do operador, abertura/avanço de etapas de produção e solicitação de materiais.",
            INSPETOR: "Inspeção seriada: consulta de histórico de fabricação por número de série, registro de não conformidades e relatórios.",
            ALMOXARIFE: "Gestão de materiais: atendimento de solicitações, baixa de insumos no estoque, cadastro de componentes e relatórios.",
        },
    ),
    MODULO_QUALIDADE: ModuloERP(
        id=MODULO_QUALIDADE,
        nome="Controle da Qualidade e Defeitos",
        sigla="QLD",
        icone=":material/verified:",
        descricao="Registro e tratamento de ocorrências de defeitos na linha, classificação de gravidade, reprovação/reprocesso e integração com manutenção.",
        categoria="Engenharia da Qualidade",
        perfis_permitidos=frozenset({ADMINISTRADOR, SUPERVISOR, INSPETOR, OPERADOR, ALMOXARIFE}),
        poder_do_perfil={
            ADMINISTRADOR: "Acesso integral: dashboard estatístico, registro, edição, ocultação de ocorrências e sincronização de cadastros.",
            SUPERVISOR: "Gestão de qualidade: dashboard de indicadores, análise de tendência e edição/auditoria do histórico de ocorrências.",
            INSPETOR: "Inspeção técnica: dashboard, registro de defeitos, edição e ocultação de ocorrências, e abertura de chamados na manutenção.",
            OPERADOR: "Apontamento em linha: visualização do dashboard, registro de ocorrências de defeito no posto e consulta ao histórico.",
            ALMOXARIFE: "Consulta técnica: visualização de indicadores e histórico de produtos reprovados para segregação de lote.",
        },
    ),
    MODULO_MANUTENCAO: ModuloERP(
        id=MODULO_MANUTENCAO,
        nome="Gestão da Manutenção de Ativos",
        sigla="MNT",
        icone=":material/build:",
        descricao="Monitoramento em tempo real das máquinas por estação (TAGs), chamados corretivos, Ordens de Serviço (O.S.), preventivas e indicadores MTTR/MTBF.",
        categoria="Engenharia de Manutenção",
        perfis_permitidos=frozenset({ADMINISTRADOR, SUPERVISOR, TECNICO, OPERADOR}),
        poder_do_perfil={
            ADMINISTRADOR: "Acesso total: controle completo de todas as seções (Operação, Manutenção Técnica e Gestão).",
            SUPERVISOR: "Gestão da manutenção: acesso exclusivo à seção de Gestão (indicadores, histórico e relatórios, cadastros e auditoria de status).",
            TECNICO: "Manutenção técnica: acesso exclusivo à seção de Manutenção Técnica (fila de chamados, preventiva e ordens de serviço, sem abertura de chamados).",
            OPERADOR: "Operação: acesso completo a toda a seção de Operação (painel de máquinas, abertura de chamados e acompanhamento de 'Meus chamados').",
        },
    ),
    MODULO_DASHBOARD: ModuloERP(
        id=MODULO_DASHBOARD,
        nome="Dashboard Industrial e Metas",
        sigla="DSH",
        icone=":material/monitoring:",
        descricao="Consolidação de indicadores industriais (meta, defeitos, retrabalho, produtividade, paradas e perdas), semáforo de alertas e importação/sincronização.",
        categoria="Inteligência Industrial",
        perfis_permitidos=frozenset({ADMINISTRADOR, SUPERVISOR, OPERADOR, INSPETOR, TECNICO}),
        poder_do_perfil={
            ADMINISTRADOR: "Acesso completo: painel executivo, produção/metas, qualidade, paradas, perdas, importação/sincronização, histórico e cadastros/limites.",
            SUPERVISOR: "Supervisão completa: painel de indicadores, lançamento de produção e metas, qualidade, paradas, perdas, sincronização e limites do semáforo.",
            OPERADOR: "Apontamento de turno: registro de produção realizada/aprovada/reprovada e apontamento de defeitos do turno.",
            INSPETOR: "Qualidade consolidada: registro de defeitos por lote de produção e controle de unidades enviadas para retrabalho.",
            TECNICO: "Controle de disponibilidade: início e encerramento de paradas de linha/máquina com cálculo automático de duração.",
        },
    ),
    MODULO_USUARIOS: ModuloERP(
        id=MODULO_USUARIOS,
        nome="Gestão de Usuários e Acessos",
        sigla="USR",
        icone=":material/manage_accounts:",
        descricao="Administração centralizada de identidades do ERP: cadastro de colaboradores, atribuição de personas, ativação/bloqueio e senhas.",
        categoria="Administração Corporativa",
        perfis_permitidos=frozenset({ADMINISTRADOR}),
        poder_do_perfil={
            ADMINISTRADOR: "Controle exclusivo de contas corporativas, matriz de permissões RBAC e sincronização automática de credenciais nos módulos.",
        },
    ),
}



def resolver_perfil_canonico(perfil_raw: str | None) -> str:
    """Normaliza qualquer variação de rótulo, código, sigla ou matrícula para uma das 6 personas canônicas."""
    s = str(perfil_raw or "").strip().lower()
    if not s:
        return OPERADOR
    if "admin" in s or s == "adm" or s.startswith("adm"):
        return ADMINISTRADOR
    if "superv" in s or "gest" in s or s == "ges" or s.startswith("ges"):
        return SUPERVISOR
    if "insp" in s or "qual" in s or s == "qua" or s.startswith("qua"):
        return INSPETOR
    if "tecn" in s or "técn" in s or "mnt" in s or s == "tec" or s.startswith("tec"):
        return TECNICO
    if "almox" in s or s == "alm" or s.startswith("alm"):
        return ALMOXARIFE
    if "oper" in s or s == "ope" or s.startswith("ope"):
        return OPERADOR
    return OPERADOR

# ============================================================
# FUNÇÕES DE CONSULTA RBAC
# ============================================================

def obter_perfil_usuario(usuario: dict | None) -> str | None:
    """Extrai o perfil/persona canônico do dicionário de usuário da sessão."""
    if not usuario:
        return None
    return resolver_perfil_canonico(usuario.get("perfil"))


def tem_acesso_modulo(usuario: dict | None, id_modulo: str) -> bool:
    """Verifica se o usuário autenticado possui poder de acesso ao módulo informado."""
    perfil = obter_perfil_usuario(usuario)
    if not perfil:
        return False
    modulo = CATALOGO_MODULOS.get(id_modulo)
    if not modulo:
        return False
    return perfil in modulo.perfis_permitidos


def modulos_permitidos(usuario: dict | None) -> list[ModuloERP]:
    """Retorna estritamente os módulos que a persona do usuário tem permissão para visualizar e utilizar."""
    perfil = obter_perfil_usuario(usuario)
    if not perfil:
        return []
    return [
        modulo for modulo in CATALOGO_MODULOS.values()
        if perfil in modulo.perfis_permitidos
    ]


def obter_papel_no_modulo(usuario: dict | None, id_modulo: str) -> str:
    """Retorna o escopo de atuação do usuário dentro do módulo especificado."""
    perfil = obter_perfil_usuario(usuario)
    if not perfil:
        return "Sem permissão"
    modulo = CATALOGO_MODULOS.get(id_modulo)
    if not modulo:
        return "Módulo inexistente"
    return modulo.poder_do_perfil.get(perfil, "Sem atribuição específica")
