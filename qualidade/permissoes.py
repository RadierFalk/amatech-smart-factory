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
