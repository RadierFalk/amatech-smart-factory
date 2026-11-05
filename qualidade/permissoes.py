"""
Autorização do Controle da Qualidade: qual perfil pode fazer o quê.

Toda a matriz fica neste arquivo. Para ajustar o que um perfil pode fazer, basta mudar o conjunto
dele em MATRIZ: as telas e as regras (ocorrencia.py, autenticacao.py) só perguntam `tem_permissao`
ou chamam `exigir`.

O perfil nunca vem de um campo da tela: ele é lido do banco (tabela usuario) a cada acesso.
"""

# ============================================================
# PERFIS
# ============================================================

ADMINISTRADOR = "Administrador"
OPERADOR = "Operador"
ALMOXARIFE = "Almoxarife"
INSPETOR = "Inspetor de Qualidade"

PERFIS = [ADMINISTRADOR, OPERADOR, ALMOXARIFE, INSPETOR]

# Prefixo da matrícula de cada perfil (ex.: OPE-0001)
PREFIXO_MATRICULA = {
    ADMINISTRADOR: "ADM",
    OPERADOR: "OPE",
    ALMOXARIFE: "ALM",
    INSPETOR: "QUA",
}

DESCRICAO_PERFIL = {
    ADMINISTRADOR: "Acesso completo ao sistema, inclusive a gestão de usuários.",
    OPERADOR: "Registra e edita ocorrências e abre chamados na Manutenção. Não oculta ocorrências.",
    ALMOXARIFE: "Somente consulta: dashboard, histórico, pesquisa e filtros.",
    INSPETOR: "Registra, edita e oculta ocorrências e abre chamados na Manutenção.",
}


# ============================================================
# PERMISSÕES
# ============================================================

VER_DASHBOARD = "ver_dashboard"
VER_HISTORICO = "ver_historico"
REGISTRAR_OCORRENCIA = "registrar_ocorrencia"
EDITAR_OCORRENCIA = "editar_ocorrencia"
OCULTAR_OCORRENCIA = "ocultar_ocorrencia"
ABRIR_CHAMADO = "abrir_chamado_manutencao"
ATUALIZAR_CADASTROS = "atualizar_cadastros"
GERENCIAR_USUARIOS = "gerenciar_usuarios"

TODAS_AS_PERMISSOES = frozenset({
    VER_DASHBOARD,
    VER_HISTORICO,
    REGISTRAR_OCORRENCIA,
    EDITAR_OCORRENCIA,
    OCULTAR_OCORRENCIA,
    ABRIR_CHAMADO,
    ATUALIZAR_CADASTROS,
    GERENCIAR_USUARIOS,
})

CONSULTA = {VER_DASHBOARD, VER_HISTORICO, ATUALIZAR_CADASTROS}

MATRIZ = {
    ADMINISTRADOR: TODAS_AS_PERMISSOES,
    OPERADOR: frozenset(CONSULTA | {REGISTRAR_OCORRENCIA, EDITAR_OCORRENCIA, ABRIR_CHAMADO}),
    ALMOXARIFE: frozenset(CONSULTA),
    INSPETOR: frozenset(CONSULTA | {REGISTRAR_OCORRENCIA, EDITAR_OCORRENCIA, OCULTAR_OCORRENCIA, ABRIR_CHAMADO}),
}

# Páginas do menu e a permissão que cada uma exige (na ordem em que aparecem)
PAGINAS = [
    ("Dashboard", VER_DASHBOARD),
    ("Registrar ocorrência", REGISTRAR_OCORRENCIA),
    ("Histórico", VER_HISTORICO),
    ("Usuários", GERENCIAR_USUARIOS),
]


class PermissaoNegada(PermissionError):
    """O perfil do usuário não permite esta operação."""


# ============================================================
# CONSULTA E EXIGÊNCIA
# ============================================================

def _perfil_de(usuario):
    if not usuario:
        return None
    return usuario["perfil"]


def tem_permissao(usuario, permissao):
    """True se o usuário (dict da sessão) tem a permissão. Sem usuário, nunca."""
    return permissao in MATRIZ.get(_perfil_de(usuario), frozenset())


def exigir(usuario, permissao):
    """Levanta PermissaoNegada se o usuário não tiver a permissão."""
    if not tem_permissao(usuario, permissao):
        raise PermissaoNegada("Seu perfil não tem permissão para realizar esta operação.")


def paginas_permitidas(usuario):
    return [nome for nome, permissao in PAGINAS if tem_permissao(usuario, permissao)]


def resolver_perfil_canonico(perfil_raw: str | None) -> str:
    """Compatibilidade para resolução de perfis do ERP AMATECH."""
    s = str(perfil_raw or "").strip().lower()
    if not s:
        return OPERADOR
    if "admin" in s or s == "adm" or s.startswith("adm"):
        return ADMINISTRADOR
    if "superv" in s or "gest" in s or s == "ges" or s.startswith("ges"):
        return "Supervisor / Gestor"
    if "insp" in s or "qual" in s or s == "qua" or s.startswith("qua"):
        return INSPETOR
    if "tecn" in s or "técn" in s or "mnt" in s or s == "tec" or s.startswith("tec"):
        return "Técnico de Manutenção"
    if "almox" in s or s == "alm" or s.startswith("alm"):
        return ALMOXARIFE
    if "oper" in s or s == "ope" or s.startswith("ope"):
        return OPERADOR
    return OPERADOR
