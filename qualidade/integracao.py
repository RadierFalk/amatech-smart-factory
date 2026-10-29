"""
Integração do Controle da Qualidade com os outros sistemas da fábrica (OA3).

- Rastreabilidade (porta 8000): dona dos números de série e dos modelos. A Qualidade busca os notebooks
  de lá e, ao registrar uma ocorrência, informa se o notebook foi reprovado, foi para reprocesso ou foi aprovado.
- Manutenção (porta 5002): dona das máquinas. A Qualidade busca as TAGs de lá e pode abrir um chamado
  quando o defeito foi causado pela máquina.

Se um sistema estiver fora do ar, a Qualidade continua funcionando: a função devolve um aviso em vez de falhar.
"""
import os

import requests

import banco


# ============================================================
# CONFIGURAÇÃO (pode ser trocada por variáveis de ambiente)
# ============================================================

RASTREABILIDADE_URL = os.environ.get("RASTREABILIDADE_URL", "http://localhost:8000").rstrip("/")
RASTREABILIDADE_CHAVE = os.environ.get("RASTREABILIDADE_CHAVE", "amt_demo_qualidade")

MANUTENCAO_URL = os.environ.get("MANUTENCAO_URL", "http://localhost:5002").rstrip("/")
MANUTENCAO_CHAVE = os.environ.get("MANUTENCAO_CHAVE", "amatech-manutencao-demo")

TEMPO_LIMITE = float(os.environ.get("INTEGRACAO_TEMPO_LIMITE", "3"))

# Prioridade do chamado de manutenção conforme a classificação do defeito
PRIORIDADE_CHAMADO = {
    "Critico": "CRITICA",
    "Maior": "ALTA",
    "Menor": "MEDIA",
}

# Etapas da Rastreabilidade em que o notebook ainda não passou pela aprovação
ETAPAS_ANTES_DA_APROVACAO = {"em fila", "em montagem", "em teste", "reprovado", "parado"}


# ============================================================
# CHAMADAS HTTP
# ============================================================

def _chamar(metodo, url, chave, corpo=None):
    """Devolve (resposta em JSON, None) ou (None, mensagem de erro). Nunca levanta exceção."""
    try:
        resposta = requests.request(
            metodo,
            url,
            json=corpo,
            headers={"X-API-Key": chave},
            timeout=TEMPO_LIMITE
        )
    except requests.RequestException:
        return None, "sistema fora do ar"

    try:
        dados = resposta.json()
    except ValueError:
        dados = {}

    if resposta.status_code >= 400:
        detalhe = dados.get("detail") if isinstance(dados, dict) else None   # formato de erro do FastAPI
        return None, detalhe or f"erro {resposta.status_code}"

    return dados, None


def _id_externo(id_ocorrencia):
    return f"QLD-{id_ocorrencia}"


# ============================================================
# CADASTROS VINDOS DOS SETORES DONOS
# ============================================================

def sincronizar_cadastros():
    """
    Busca os notebooks (série e modelo) na Rastreabilidade e as máquinas (TAG) na Manutenção.
    Só acrescenta o que falta; nada é apagado. Devolve uma lista de (tipo, mensagem), tipo = sucesso ou aviso.
    """
    mensagens = []

    producoes, erro = _chamar("GET", f"{RASTREABILIDADE_URL}/api/v1/producoes?limite=1000", RASTREABILIDADE_CHAVE)
    if erro:
        mensagens.append(("aviso", f"Rastreabilidade: não foi possível buscar os notebooks ({erro})."))
    else:
        novos = sum(
            banco.inserir_produto_se_novo(p["numero_serie"], p["modelo"]["nome"])
            for p in producoes
        )
        mensagens.append(("sucesso", f"Rastreabilidade: {len(producoes)} notebooks consultados, {novos} novos."))

    maquinas, erro = _chamar("GET", f"{MANUTENCAO_URL}/api/equipamentos", MANUTENCAO_CHAVE)
    if erro:
        mensagens.append(("aviso", f"Manutenção: não foi possível buscar as máquinas ({erro})."))
    else:
        novas = sum(
            banco.inserir_maquina_se_nova(m["codigo_tag"], m["nome"])
            for m in maquinas
        )
        mensagens.append(("sucesso", f"Manutenção: {len(maquinas)} máquinas consultadas, {novas} novas."))

    return mensagens


# ============================================================
# AVISOS DE UMA OCORRÊNCIA REGISTRADA
# ============================================================

def _mudar_etapa(serie, status, corpo_extra=None):
    corpo = {"status": status, "maquina": "Controle da Qualidade"}
    corpo.update(corpo_extra or {})
    return _chamar(
        "POST",
        f"{RASTREABILIDADE_URL}/api/v1/producoes/{serie}/status",
        RASTREABILIDADE_CHAVE,
        corpo
    )


def informar_rastreabilidade(ocorrencia):
    """
    Reprovado      -> etapa "Reprovado", com a falha e o motivo reais (a Rastreabilidade registra a NC).
    Em_reprocesso  -> "Reprovado" e, em seguida, "Em Montagem" (o notebook volta para a linha).
    Aprovado       -> "Aprovado", se o notebook ainda não tiver passado pela aprovação.
    """
    serie = ocorrencia["numero_serie_produto"]
    situacao = ocorrencia["situacao_produto"]
    reprovacao = {
        "descricao_falha": ocorrencia["observacao_ocorrencia"],
        "motivo_reprovacao": f"{ocorrencia['nome_tipo_defeito']} ({ocorrencia['classificacao_defeito']})",
        "id_externo": _id_externo(ocorrencia["id_ocorrencia"]),
    }

    if situacao in ("Reprovado", "Em_reprocesso"):
        resposta, erro = _mudar_etapa(serie, "Reprovado", reprovacao)
        if erro:
            return "aviso", f"Rastreabilidade: o notebook {serie} não foi atualizado ({erro})."
        if not resposta["alterado"]:   # esta ocorrência já tinha sido informada
            return "sucesso", f"Rastreabilidade: a reprovação de {serie} já estava registrada."
        if situacao == "Reprovado":
            return "sucesso", f"Rastreabilidade: {serie} marcado como Reprovado."
        _, erro = _mudar_etapa(serie, "Em Montagem")
        if erro:
            return "aviso", f"Rastreabilidade: {serie} reprovado, mas não voltou para a montagem ({erro})."
        return "sucesso", f"Rastreabilidade: {serie} reprovado e devolvido para Em Montagem (reprocesso)."

    producao, erro = _chamar("GET", f"{RASTREABILIDADE_URL}/api/v1/producoes/{serie}", RASTREABILIDADE_CHAVE)
    if erro:
        return "aviso", f"Rastreabilidade: não foi possível consultar o notebook {serie} ({erro})."
    if producao["status"].lower() not in ETAPAS_ANTES_DA_APROVACAO:
        return "sucesso", f"Rastreabilidade: {serie} já está em {producao['status']}; nada a alterar."
    _, erro = _mudar_etapa(serie, "Aprovado")
    if erro:
        return "aviso", f"Rastreabilidade: o notebook {serie} não foi aprovado ({erro})."
    return "sucesso", f"Rastreabilidade: {serie} marcado como Aprovado."


def abrir_chamado_manutencao(ocorrencia):
    """Defeito causado pela máquina: abre um chamado na Manutenção para a TAG da ocorrência."""
    corpo = {
        "equipamento_tag": ocorrencia["nome_maquina"],
        "descricao_falha": (
            f"{ocorrencia['nome_tipo_defeito']} em {ocorrencia['numero_serie_produto']}: "
            f"{ocorrencia['observacao_ocorrencia']} (ocorrência {_id_externo(ocorrencia['id_ocorrencia'])} da Qualidade)"
        ),
        "prioridade": PRIORIDADE_CHAMADO.get(ocorrencia["classificacao_defeito"], "MEDIA"),
        "tipo_manutencao": "CORRETIVA",
        "origem_sistema": "qualidade",
        "id_externo": _id_externo(ocorrencia["id_ocorrencia"]),
    }
    dados, erro = _chamar("POST", f"{MANUTENCAO_URL}/api/manutencao/chamados", MANUTENCAO_CHAVE, corpo)
    if erro:
        return "aviso", f"Manutenção: o chamado não foi aberto ({erro})."
    if not dados["criado"]:
        return "sucesso", f"Manutenção: o chamado #{dados['id_chamado']} desta ocorrência já estava aberto."
    return "sucesso", f"Manutenção: chamado #{dados['id_chamado']} aberto para a máquina {ocorrencia['nome_maquina']}."


def notificar_ocorrencia(id_ocorrencia, abrir_chamado=False):
    """Avisa os outros sistemas sobre uma ocorrência recém-registrada. Devolve uma lista de (tipo, mensagem)."""
    ocorrencia = banco.buscar_ocorrencia_detalhada(id_ocorrencia)
    if ocorrencia is None:
        return [("aviso", "Ocorrência não encontrada.")]

    mensagens = [informar_rastreabilidade(ocorrencia)]
    if abrir_chamado:
        mensagens.append(abrir_chamado_manutencao(ocorrencia))
    return mensagens
