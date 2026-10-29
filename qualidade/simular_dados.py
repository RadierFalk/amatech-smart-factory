import random
from datetime import date, timedelta

import banco


# ============================================================
# CONFIGURAÇÃO
# ============================================================

QUANTIDADE_PADRAO = 50

CLASSIFICACOES = [
    "Critico",
    "Maior",
    "Menor"
]

SITUACOES = [
    "Aprovado",
    "Reprovado",
    "Em_reprocesso"
]

STATUS = [
    "Aberta",
    "Em_analise",
    "Resolvida"
]


# ============================================================
# PESOS DOS TIPOS DE DEFEITO
# ============================================================

PESOS_DEFEITOS = {
    "Tela": 16,
    "Bateria": 13,
    "Teclado": 12,
    "Wi-Fi": 10,
    "Câmera": 9,
    "Áudio": 8,
    "USB": 7,
    "Touchpad": 6,
    "Armazenamento": 5,
    "Desempenho": 5,
    "Software": 5,
    "Montagem": 4
}


# ============================================================
# PESOS DAS ESTAÇÕES
# ============================================================

PESOS_ESTACOES = {
    "Teste Funcional": 30,
    "Inspeção de Qualidade": 22,
    "Montagem Final": 15,
    "Instalação de Software": 12,
    "Inserção Manual": 9,
    "SMT": 7,
    "Embalagem": 5
}


# ============================================================
# ESCOLHA COM PESO
# ============================================================

def escolher_com_peso(dicionario):

    itens = list(dicionario.keys())
    pesos = list(dicionario.values())

    return random.choices(
        itens,
        weights=pesos,
        k=1
    )[0]


# ============================================================
# GERAÇÃO DE OCORRÊNCIA
# ============================================================

def gerar_ocorrencia(
    produtos,
    estacoes,
    tipos_defeito,
    maquinas,
    usuarios,
    data_base
):

    produto = random.choice(produtos)

    # --------------------------------------------------------
    # Tipo de defeito
    # --------------------------------------------------------

    nomes_tipos_disponiveis = [
        item["nome_tipo_defeito"]
        for item in tipos_defeito
    ]

    pesos_tipos_validos = {
        nome: peso
        for nome, peso in PESOS_DEFEITOS.items()
        if nome in nomes_tipos_disponiveis
    }

    nome_defeito = escolher_com_peso(
        pesos_tipos_validos
    )

    tipo_defeito = next(
        item
        for item in tipos_defeito
        if item["nome_tipo_defeito"] == nome_defeito
    )

    # --------------------------------------------------------
    # Estação
    # --------------------------------------------------------

    nomes_estacoes_disponiveis = [
        item["nome_estacao"]
        for item in estacoes
    ]

    pesos_estacoes_validos = {
        nome: peso
        for nome, peso in PESOS_ESTACOES.items()
        if nome in nomes_estacoes_disponiveis
    }

    nome_estacao = escolher_com_peso(
        pesos_estacoes_validos
    )

    estacao = next(
        item
        for item in estacoes
        if item["nome_estacao"] == nome_estacao
    )

    # --------------------------------------------------------
    # Máquina
    # --------------------------------------------------------

    maquina = random.choice(maquinas)

    # --------------------------------------------------------
    # Usuário
    # --------------------------------------------------------

    usuario = random.choice(usuarios)

    # --------------------------------------------------------
    # Classificação
    # --------------------------------------------------------

    classificacao = random.choices(
        CLASSIFICACOES,
        weights=[15, 45, 40],
        k=1
    )[0]

    # --------------------------------------------------------
    # Situação do produto
    # --------------------------------------------------------

    situacao = random.choices(
        SITUACOES,
        weights=[35, 40, 25],
        k=1
    )[0]

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    status = random.choices(
        STATUS,
        weights=[20, 20, 60],
        k=1
    )[0]

    # --------------------------------------------------------
    # Data
    # --------------------------------------------------------

    dias_atras = random.randint(
        0,
        13
    )

    data_ocorrencia = (
        data_base
        - timedelta(days=dias_atras)
    ).strftime("%Y-%m-%d")

    # --------------------------------------------------------
    # Hora
    # --------------------------------------------------------

    hora_ocorrencia = (
        f"{random.randint(7, 17):02d}:"
        f"{random.randint(0, 59):02d}:"
        f"{random.randint(0, 59):02d}"
    )

    # --------------------------------------------------------
    # Textos
    # --------------------------------------------------------

    observacoes = [
        "Falha identificada durante a inspeção.",
        "Defeito identificado durante o teste funcional.",
        "Problema detectado durante a verificação do produto.",
        "Falha registrada durante o processo produtivo.",
        "Componente apresentou comportamento fora do esperado.",
        "Necessária análise do produto antes da liberação."
    ]

    acoes = [
        "Produto encaminhado para análise.",
        "Componente substituído.",
        "Produto encaminhado para reprocesso.",
        "Falha corrigida e novo teste realizado.",
        "Produto separado para avaliação da qualidade.",
        "Ajuste realizado na estação."
    ]

    return {
        "data_ocorrencia": data_ocorrencia,
        "hora_ocorrencia": hora_ocorrencia,
        "classificacao_defeito": classificacao,
        "situacao_produto": situacao,
        "observacao_ocorrencia": random.choice(
            observacoes
        ),
        "acao_realizada": random.choice(
            acoes
        ),
        "status_ocorrencia": status,
        "visibilidade_ocorrencia": "Visivel",
        "id_produto": produto["id_produto"],
        "id_estacao": estacao["id_estacao"],
        "id_tipo_defeito": tipo_defeito["id_tipo_defeito"],
        "id_maquina": maquina["id_maquina"],
        "id_usuario": usuario["id_usuario"]
    }


# ============================================================
# INSERÇÃO NO BANCO
# ============================================================

def inserir_ocorrencia(dados):

    conexao = banco.conectar()

    cursor = conexao.cursor()

    cursor.execute(
        """
        INSERT INTO ocorrencia (
            data_ocorrencia,
            hora_ocorrencia,
            classificacao_defeito,
            situacao_produto,
            observacao_ocorrencia,
            acao_realizada,
            status_ocorrencia,
            visibilidade_ocorrencia,
            id_produto,
            id_estacao,
            id_tipo_defeito,
            id_maquina,
            id_usuario
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dados["data_ocorrencia"],
            dados["hora_ocorrencia"],
            dados["classificacao_defeito"],
            dados["situacao_produto"],
            dados["observacao_ocorrencia"],
            dados["acao_realizada"],
            dados["status_ocorrencia"],
            dados["visibilidade_ocorrencia"],
            dados["id_produto"],
            dados["id_estacao"],
            dados["id_tipo_defeito"],
            dados["id_maquina"],
            dados["id_usuario"]
        )
    )

    conexao.commit()
    conexao.close()


# ============================================================
# EXECUÇÃO
# ============================================================

def main():

    print("=" * 60)
    print("SIMULADOR DE DADOS - CONTROLE DA QUALIDADE")
    print("=" * 60)

    entrada = input(
        f"Quantidade de ocorrências a gerar "
        f"(Enter = {QUANTIDADE_PADRAO}): "
    ).strip()

    if entrada == "":
        quantidade = QUANTIDADE_PADRAO

    else:
        try:
            quantidade = int(entrada)

        except ValueError:
            print("Quantidade inválida.")
            return

    if quantidade <= 0:
        print("A quantidade deve ser maior que zero.")
        return

    # --------------------------------------------------------
    # Carrega dados existentes
    # --------------------------------------------------------

    try:

        produtos = banco.listar_produtos()
        estacoes = banco.listar_estacoes()
        tipos_defeito = banco.listar_tipos_defeito()
        maquinas = banco.listar_maquinas()
        usuarios = banco.listar_usuarios()

    except Exception as erro:

        print(
            f"Erro ao carregar dados do banco: {erro}"
        )

        return

    # --------------------------------------------------------
    # Validação
    # --------------------------------------------------------

    if not produtos:
        print("Nenhum produto encontrado.")
        return

    if not estacoes:
        print("Nenhuma estação encontrada.")
        return

    if not tipos_defeito:
        print("Nenhum tipo de defeito encontrado.")
        return

    if not maquinas:
        print("Nenhuma máquina encontrada.")
        return

    if not usuarios:
        print("Nenhum usuário encontrado.")
        return

    # --------------------------------------------------------
    # Geração
    # --------------------------------------------------------

    data_base = date.today()

    print()
    print(
        f"Gerando {quantidade} ocorrências..."
    )

    for _ in range(quantidade):

        dados = gerar_ocorrencia(
            produtos,
            estacoes,
            tipos_defeito,
            maquinas,
            usuarios,
            data_base
        )

        inserir_ocorrencia(dados)

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("DADOS SIMULADOS ADICIONADOS COM SUCESSO")
    print("=" * 60)

    ocorrencias = banco.listar_ocorrencias()

    print(
        f"Ocorrências visíveis no banco: "
        f"{len(ocorrencias)}"
    )

    print()
    print(
        "O dashboard já pode ser atualizado "
        "para visualizar os novos dados."
    )


if __name__ == "__main__":
    main()