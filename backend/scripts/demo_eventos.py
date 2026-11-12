"""Chamados da Manutenção e ocorrências da Qualidade dos últimos 7 dias, usados pelo seed_demo.

Sem eles, as abas Manutenção e Qualidade do Dashboard abrem vazias numa demonstração. As datas são relativas a
hoje (dia da fábrica, Manaus): a demonstração mostra sempre a última semana preenchida. Uma máquina (TEST-02)
fica parada com um chamado em andamento, para o aviso de "parada agora" aparecer.

Só povoa tabelas vazias. Grava direto nas tabelas, sem passar pelas integrações (QLD -> RAS/MNT): são dados de vitrine.
"""
from datetime import datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.modulos.manutencao.constantes import StatusEquipamento
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.usuarios.modelos import Usuario

# dias atrás, hora de abertura, min até o técnico assumir, min de reparo, máquina, causa raiz, falha relatada
CHAMADOS = [
    (6, time(8, 20), 9, 45, "MONT-01", "Desgaste mecânico", "Parafusadeira travando"),
    (5, time(15, 10), 14, 30, "SMT-02", "Falha de sensor", "Sensor de posição sem leitura"),
    (4, time(9, 40), 11, 92, "TEST-03", "Falha elétrica", "Fonte do testador desarmando"),
    (3, time(16, 5), 7, 35, "INS-01", "Erro de operação", "Programa errado carregado"),
    (2, time(10, 30), 18, 64, "MONT-01", "Desgaste mecânico", "Correia da esteira folgada"),
    (1, time(7, 50), 12, 99, "SMT-02", "Falha de sensor", "Leitor de fiducial descalibrado"),
    (1, time(17, 25), 10, 41, "TEST-03", "Falha elétrica", "Cabo de alimentação com mau contato"),
]
PARADA_AGORA = ("TEST-02", "Sondas do ICT sem contato")

# Máquina de cada estação (a ocorrência aponta o equipamento onde o defeito apareceu).
MAQUINA_DA_ESTACAO = {"SMT": "SMT-01", "Inserção Manual": "INS-01", "Montagem Final": "MONT-01",
                      "Instalação de Software": "TEST-01", "Teste Funcional": "TEST-03",
                      "Inspeção de Qualidade": "QC-01", "Embalagem": "EMB-01"}

# dias atrás, hora, estação, defeito, gravidade, situação do notebook, status
OCORRENCIAS = [
    (6, time(9, 15), "Teste Funcional", "Tela", "MAIOR", "EM_REPROCESSO", "RESOLVIDA"),
    (6, time(15, 40), "Montagem Final", "Teclado", "MENOR", "APROVADO", "RESOLVIDA"),
    (5, time(10, 5), "SMT", "Montagem", "MAIOR", "EM_REPROCESSO", "RESOLVIDA"),
    (5, time(16, 20), "Teste Funcional", "Wi-Fi", "MAIOR", "EM_REPROCESSO", "RESOLVIDA"),
    (4, time(8, 30), "Teste Funcional", "Bateria", "CRITICO", "REPROVADO", "RESOLVIDA"),
    (4, time(13, 10), "Inspeção de Qualidade", "Tela", "MENOR", "APROVADO", "RESOLVIDA"),
    (3, time(9, 50), "Montagem Final", "Teclado", "MENOR", "EM_REPROCESSO", "RESOLVIDA"),
    (3, time(17, 5), "Teste Funcional", "Tela", "MAIOR", "EM_REPROCESSO", "EM_ANALISE"),
    (2, time(7, 45), "Instalação de Software", "Software", "MENOR", "EM_REPROCESSO", "RESOLVIDA"),
    (2, time(11, 30), "SMT", "Armazenamento", "MAIOR", "EM_REPROCESSO", "EM_ANALISE"),
    (2, time(19, 15), "Teste Funcional", "Áudio", "MENOR", "APROVADO", "RESOLVIDA"),
    (1, time(8, 10), "Teste Funcional", "Tela", "CRITICO", "REPROVADO", "EM_ANALISE"),
    (1, time(14, 35), "Montagem Final", "Touchpad", "MAIOR", "EM_REPROCESSO", "ABERTA"),
    (1, time(18, 50), "Inserção Manual", "USB", "MENOR", "EM_REPROCESSO", "ABERTA"),
    (0, time(7, 20), "Teste Funcional", "Bateria", "CRITICO", "REPROVADO", "ABERTA"),
    (0, time(9, 5), "Teste Funcional", "Wi-Fi", "MAIOR", "EM_REPROCESSO", "ABERTA"),
]


def _no_dia(dias_atras: int, hora: time) -> datetime:
    hoje = tempo.agora().astimezone(tempo.FUSO_FABRICA).date()
    return datetime.combine(hoje - timedelta(days=dias_atras), hora, tempo.FUSO_FABRICA)


def popular(sessao: Session, pessoas: dict[str, Usuario]) -> list[str]:
    feito = []
    agora = tempo.agora()
    maquinas = {e.codigo_tag: e for e in sessao.scalars(select(Equipamento))}
    operador, tecnico, inspetor = pessoas.get("OPE-0001"), pessoas.get("TEC-2001"), pessoas.get("QUA-0001")

    if operador and tecnico and not sessao.scalar(select(Chamado.id).limit(1)):
        n = 0
        for dias, hora, resposta, reparo, tag, causa, falha in CHAMADOS:
            if tag not in maquinas:
                continue
            abertura = _no_dia(dias, hora)
            inicio = abertura + timedelta(minutes=resposta)
            sessao.add(Chamado(
                equipamento_id=maquinas[tag].id, operador_abertura_id=operador.id, tecnico_responsavel_id=tecnico.id,
                prioridade="ALTA", tipo_manutencao="CORRETIVA", status_chamado="CONCLUIDO", descricao_falha=falha,
                diagnostico_tecnico="Ajuste e troca da peça", causa_raiz=causa, data_hora_abertura=abertura,
                data_hora_inicio_atendimento=inicio, data_hora_fim_atendimento=inicio + timedelta(minutes=reparo),
                downtime_minutos=resposta + reparo))
            n += 1
        tag, falha = PARADA_AGORA
        if tag in maquinas:
            # Parada desde as 07:30 de hoje (ou há 3 h, se ainda for cedo): o chamado está em atendimento.
            abertura = min(max(_no_dia(0, time(7, 30)), agora - timedelta(hours=3)), agora - timedelta(minutes=20))
            sessao.add(Chamado(
                equipamento_id=maquinas[tag].id, operador_abertura_id=operador.id, tecnico_responsavel_id=tecnico.id,
                prioridade="CRITICA", tipo_manutencao="CORRETIVA", status_chamado="EM_ANDAMENTO", descricao_falha=falha,
                data_hora_abertura=abertura, data_hora_inicio_atendimento=abertura + timedelta(minutes=12)))
            maquinas[tag].status_operacional = StatusEquipamento.PARADA.value
            n += 1
        feito.append(f"mnt.chamados: {n} chamados dos últimos 7 dias ({tag} parada agora)")

    if inspetor and not sessao.scalar(select(Ocorrencia.id).limit(1)):
        estacoes = {e.nome: e.id for e in sessao.scalars(select(Estacao))}
        tipos = {t.nome: t.id for t in sessao.scalars(select(TipoDefeito))}
        produtos = list(sessao.scalars(select(Produto).order_by(Produto.id)))
        n = 0
        for i, (dias, hora, estacao, defeito, gravidade, situacao, status) in enumerate(OCORRENCIAS):
            quando = _no_dia(dias, hora)
            maquina = maquinas.get(MAQUINA_DA_ESTACAO.get(estacao, ""))
            if quando > agora or not produtos or estacao not in estacoes or defeito not in tipos or not maquina:
                continue
            sessao.add(Ocorrencia(
                ocorrida_em=quando, classificacao=gravidade, situacao_produto=situacao, status=status,
                observacao=f"{defeito}: defeito encontrado na estação {estacao}", acao_realizada="Retido para análise",
                produto_id=produtos[i % len(produtos)].id, estacao_id=estacoes[estacao], tipo_defeito_id=tipos[defeito],
                equipamento_id=maquina.id, responsavel_id=inspetor.id))
            n += 1
        feito.append(f"qld.ocorrencias: {n} ocorrências dos últimos 7 dias")
    return feito
