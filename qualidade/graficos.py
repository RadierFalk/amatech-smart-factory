import banco
from collections import Counter


# ============================================================
# OCORRÊNCIAS POR TIPO DE DEFEITO
# ============================================================

def ocorrencias_por_tipo_defeito():

    ocorrencias = banco.listar_ocorrencias()

    contagem = Counter(
        ocorrencia["nome_tipo_defeito"]
        for ocorrencia in ocorrencias
    )

    return dict(contagem.most_common())


# ============================================================
# OCORRÊNCIAS POR ESTAÇÃO
# ============================================================

def ocorrencias_por_estacao():

    ocorrencias = banco.listar_ocorrencias()

    contagem = Counter(
        ocorrencia["nome_estacao"]
        for ocorrencia in ocorrencias
    )

    return dict(contagem.most_common())


# ============================================================
# TENDÊNCIA DE OCORRÊNCIAS
# ============================================================

def ocorrencias_por_data():

    ocorrencias = banco.listar_ocorrencias()

    contagem = Counter(
        ocorrencia["data_ocorrencia"]
        for ocorrencia in ocorrencias
    )

    dados = sorted(
        contagem.items(),
        key=lambda item: item[0]
    )

    datas = [
        item[0]
        for item in dados
    ]

    quantidades = [
        item[1]
        for item in dados
    ]

    return datas, quantidades