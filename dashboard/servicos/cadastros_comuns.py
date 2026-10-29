"""Cadastros comuns do ecossistema AMATECH Smart Factory (OA3).

Cada setor tem o seu sistema, e os nomes nem sempre são escritos igual (ex.: "SMT" na Qualidade e
"Linha SMT" aqui). Este arquivo diz qual nome do Dashboard corresponde a cada nome usado nos outros
sistemas. A comparação ignora maiúsculas, acentos e espaços extras, então só as diferenças de verdade
precisam estar aqui. Documentação completa: docs/CADASTROS_COMUNS.md.

Quem é o "dono" de cada cadastro:
  - Modelos de notebook e números de série: Rastreabilidade (Projeto 2)
  - Máquinas (tags como TEST-01):           Manutenção (Projeto 5)
  - Estações, turnos e tipos de defeito:    lista abaixo, aceita pelos quatro sistemas
"""
import unicodedata


def normalizar(texto):
    """'Inspeção de Qualidade ' -> 'inspecao de qualidade' (sem acento, minúsculo, espaços simples)."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().split())


# nome usado em outro sistema (já normalizado) -> nome cadastrado no Dashboard
SINONIMOS = {
    "estacao": {
        "smt": "Linha SMT",                                   # Qualidade e Manutenção
        "inspecao de qualidade": "Inspeção da qualidade",     # Qualidade
        "testes funcionais": "Teste funcional",               # Manutenção
        "testes": "Teste funcional",
    },
    "tipo_defeito": {                                        # tipos da Qualidade
        "tela": "Tela com defeito",
        "teclado": "Falha no teclado",
        "touchpad": "Falha no touchpad",
        "usb": "Falha de USB",
        "audio": "Falha de áudio",
        "wi-fi": "Falha no Wi-Fi",
        "camera": "Falha na câmera",
        "bateria": "Falha na bateria",
        "armazenamento": "Falha no armazenamento",
        "desempenho": "Desempenho insuficiente",
        "montagem": "Falha de montagem",
        "software": "Falha de software",
    },
    "motivo_parada": {                                       # tipo de manutenção da Manutenção
        "corretiva": "Falha de equipamento",
        "preventiva": "Manutenção programada",
    },
    "turno": {
        "1": "1º turno", "primeiro turno": "1º turno", "turno 1": "1º turno",
        "2": "2º turno", "segundo turno": "2º turno", "turno 2": "2º turno",
    },
}

# Para onde volta um notebook em reprocesso na Qualidade (a Rastreabilidade o devolve para "Em Montagem")
ESTACAO_RETORNO_REPROCESSO = "Montagem final"
