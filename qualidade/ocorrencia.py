from datetime import date, datetime, time

import banco


# ============================================================
# VALORES PERMITIDOS
# ============================================================

CLASSIFICACOES_DEFEITO = [
    "Critico",
    "Maior",
    "Menor"
]

SITUACOES_PRODUTO = [
    "Aprovado",
    "Reprovado",
    "Em_reprocesso"
]

STATUS_OCORRENCIA = [
    "Aberta",
    "Em_analise",
    "Resolvida"
]


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_ocorrencia(
    data_ocorrencia,
    hora_ocorrencia,
    classificacao_defeito,
    situacao_produto,
    observacao_ocorrencia,
    acao_realizada,
    status_ocorrencia,
    id_produto,
    id_estacao,
    id_tipo_defeito,
    id_maquina,
    id_usuario
):
    erros = []

    if not data_ocorrencia:
        erros.append("A data da ocorrência é obrigatória.")

    if not hora_ocorrencia:
        erros.append("A hora da ocorrência é obrigatória.")

    if classificacao_defeito not in CLASSIFICACOES_DEFEITO:
        erros.append("Classificação de defeito inválida.")

    if situacao_produto not in SITUACOES_PRODUTO:
        erros.append("Situação do produto inválida.")

    if status_ocorrencia not in STATUS_OCORRENCIA:
        erros.append("Status da ocorrência inválido.")

    if not id_produto:
        erros.append("O produto é obrigatório.")

    if not id_estacao:
        erros.append("A estação é obrigatória.")

    if not id_tipo_defeito:
        erros.append("O tipo de defeito é obrigatório.")

    if not id_maquina:
        erros.append("A máquina é obrigatória.")

    if not id_usuario:
        erros.append("O usuário é obrigatório.")

    if not observacao_ocorrencia or not observacao_ocorrencia.strip():
        erros.append("A observação da ocorrência é obrigatória.")

    if not acao_realizada or not acao_realizada.strip():
        erros.append("A ação realizada é obrigatória.")

    return erros


# ============================================================
# REGISTRAR OCORRÊNCIA
# ============================================================

def registrar_ocorrencia(
    data_ocorrencia,
    hora_ocorrencia,
    classificacao_defeito,
    situacao_produto,
    observacao_ocorrencia,
    acao_realizada,
    status_ocorrencia,
    id_produto,
    id_estacao,
    id_tipo_defeito,
    id_maquina,
    id_usuario
):
    erros = validar_ocorrencia(
        data_ocorrencia,
        hora_ocorrencia,
        classificacao_defeito,
        situacao_produto,
        observacao_ocorrencia,
        acao_realizada,
        status_ocorrencia,
        id_produto,
        id_estacao,
        id_tipo_defeito,
        id_maquina,
        id_usuario
    )

    if erros:
        return False, erros

    if isinstance(data_ocorrencia, date):
        data_ocorrencia = data_ocorrencia.isoformat()

    if isinstance(hora_ocorrencia, datetime):
        hora_ocorrencia = hora_ocorrencia.time()

    if isinstance(hora_ocorrencia, time):
        hora_ocorrencia = hora_ocorrencia.strftime("%H:%M:%S")

    id_ocorrencia = banco.registrar_ocorrencia(
        data_ocorrencia=data_ocorrencia,
        hora_ocorrencia=hora_ocorrencia,
        classificacao_defeito=classificacao_defeito,
        situacao_produto=situacao_produto,
        observacao_ocorrencia=observacao_ocorrencia.strip(),
        acao_realizada=acao_realizada.strip(),
        status_ocorrencia=status_ocorrencia,
        id_produto=id_produto,
        id_estacao=id_estacao,
        id_tipo_defeito=id_tipo_defeito,
        id_maquina=id_maquina,
        id_usuario=id_usuario
    )

    return True, id_ocorrencia


# ============================================================
# EDITAR OCORRÊNCIA
# ============================================================

def editar_ocorrencia(
    id_ocorrencia,
    data_ocorrencia,
    hora_ocorrencia,
    classificacao_defeito,
    situacao_produto,
    observacao_ocorrencia,
    acao_realizada,
    status_ocorrencia,
    id_produto,
    id_estacao,
    id_tipo_defeito,
    id_maquina,
    id_usuario
):
    if not id_ocorrencia:
        return False, ["Identificador da ocorrência não informado."]

    erros = validar_ocorrencia(
        data_ocorrencia,
        hora_ocorrencia,
        classificacao_defeito,
        situacao_produto,
        observacao_ocorrencia,
        acao_realizada,
        status_ocorrencia,
        id_produto,
        id_estacao,
        id_tipo_defeito,
        id_maquina,
        id_usuario
    )

    if erros:
        return False, erros

    ocorrencia = banco.buscar_ocorrencia(id_ocorrencia)

    if ocorrencia is None:
        return False, ["Ocorrência não encontrada."]

    if isinstance(data_ocorrencia, date):
        data_ocorrencia = data_ocorrencia.isoformat()

    if isinstance(hora_ocorrencia, datetime):
        hora_ocorrencia = hora_ocorrencia.time()

    if isinstance(hora_ocorrencia, time):
        hora_ocorrencia = hora_ocorrencia.strftime("%H:%M:%S")

    banco.editar_ocorrencia(
        id_ocorrencia=id_ocorrencia,
        data_ocorrencia=data_ocorrencia,
        hora_ocorrencia=hora_ocorrencia,
        classificacao_defeito=classificacao_defeito,
        situacao_produto=situacao_produto,
        observacao_ocorrencia=observacao_ocorrencia.strip(),
        acao_realizada=acao_realizada.strip(),
        status_ocorrencia=status_ocorrencia,
        id_produto=id_produto,
        id_estacao=id_estacao,
        id_tipo_defeito=id_tipo_defeito,
        id_maquina=id_maquina,
        id_usuario=id_usuario
    )

    return True, None


# ============================================================
# OCULTAR OCORRÊNCIA
# ============================================================

def ocultar_ocorrencia(id_ocorrencia):
    if not id_ocorrencia:
        return False, "Identificador da ocorrência não informado."

    ocorrencia = banco.buscar_ocorrencia(id_ocorrencia)

    if ocorrencia is None:
        return False, "Ocorrência não encontrada."

    if ocorrencia["visibilidade_ocorrencia"] == "Oculta":
        return False, "A ocorrência já está oculta."

    banco.ocultar_ocorrencia(id_ocorrencia)

    return True, None


# ============================================================
# CONSULTAS
# ============================================================

def listar_ocorrencias():
    return banco.listar_ocorrencias()


def pesquisar_ocorrencias(termo):
    if not termo or not termo.strip():
        return banco.listar_ocorrencias()

    return banco.pesquisar_ocorrencias(termo.strip())


def filtrar_ocorrencias(
    tipo_defeito=None,
    estacao=None,
    classificacao=None,
    status=None
):
    return banco.filtrar_ocorrencias(
        tipo_defeito=tipo_defeito,
        estacao=estacao,
        classificacao=classificacao,
        status=status
    )


def buscar_ocorrencia(id_ocorrencia):
    return banco.buscar_ocorrencia(id_ocorrencia)