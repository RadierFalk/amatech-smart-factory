import banco


# ============================================================
# TOTAL DE OCORRÊNCIAS
# ============================================================

def total_ocorrencias():
    ocorrencias = banco.listar_ocorrencias()
    return len(ocorrencias)


# ============================================================
# OCORRÊNCIAS ABERTAS
# ============================================================

def ocorrencias_abertas():
    ocorrencias = banco.listar_ocorrencias()

    return sum(
        1
        for ocorrencia in ocorrencias
        if ocorrencia["status_ocorrencia"] == "Aberta"
    )


# ============================================================
# PRODUTOS REPROVADOS
# ============================================================

def produtos_reprovados():
    ocorrencias = banco.listar_ocorrencias()

    produtos = {
        ocorrencia["numero_serie_produto"]
        for ocorrencia in ocorrencias
        if ocorrencia["situacao_produto"] == "Reprovado"
    }

    return len(produtos)


# ============================================================
# ESTAÇÃO COM MAIS OCORRÊNCIAS
# ============================================================

def estacao_com_mais_ocorrencias():
    ocorrencias = banco.listar_ocorrencias()

    if not ocorrencias:
        return None

    contagem = {}

    for ocorrencia in ocorrencias:
        estacao = ocorrencia["nome_estacao"]

        if estacao not in contagem:
            contagem[estacao] = 0

        contagem[estacao] += 1

    return max(contagem, key=contagem.get)


# ============================================================
# TODOS OS INDICADORES
# ============================================================

def obter_indicadores():
    return {
        "total_ocorrencias": total_ocorrencias(),
        "ocorrencias_abertas": ocorrencias_abertas(),
        "produtos_reprovados": produtos_reprovados(),
        "estacao_com_mais_ocorrencias": estacao_com_mais_ocorrencias()
    }