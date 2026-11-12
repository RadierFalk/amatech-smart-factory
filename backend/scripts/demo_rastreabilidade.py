"""Dados de demonstração da Rastreabilidade (portados de rastreabilidade/app/seed.py), usados pelo seed_demo.

30 produções (AMT-000001 a AMT-000030, os mesmos números de série dos notebooks da Qualidade) espalhadas
pelos últimos 7 dias, com histórico de etapas, não conformidades e o fluxo de materiais.
"""
import random
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.modulos.rastreabilidade.constantes import ETAPAS_PADRAO, PREFIXO_SERIE, StatusSolicitacao
from app.modulos.rastreabilidade.modelos import (
    Baixa,
    Componente,
    Etapa,
    Modelo,
    ModeloComponente,
    NaoConformidade,
    Passagem,
    Producao,
    Solicitacao,
)
from app.modulos.usuarios.modelos import Usuario

COMPONENTES = [  # sku, nome, estoque inicial
    ("PCB-MB-001", "Placa-mãe AMT", 420), ("CPU-I5-12", "Processador Intel Core i5", 350),
    ("CPU-I7-13", "Processador Intel Core i7", 260), ("RAM-8G-D4", "Memória RAM 8GB DDR4", 800),
    ("RAM-16G-D4", "Memória RAM 16GB DDR4", 520), ("SSD-256-NV", "SSD 256GB NVMe", 610),
    ("SSD-512-NV", "SSD 512GB NVMe", 430), ("LCD-14-FHD", 'Tela LCD 14" Full HD', 300),
    ("LCD-156-FHD", 'Tela LCD 15,6" Full HD', 330), ("KBD-ABNT2", "Teclado ABNT2", 700),
    ("TPD-001", "Touchpad", 650), ("BAT-45WH", "Bateria 45Wh", 280), ("PSU-65W", "Fonte 65W", 540),
    ("CHS-001", "Gabinete (carcaça)", 470), ("COOL-001", "Sistema de refrigeração", 390),
    ("BOX-001", "Caixa de embalagem", 900), ("MAN-001", "Manual do usuário", 1000),
    ("LBL-001", "Etiqueta de série", 1200),
]

_BASE = ["PCB-MB-001", "KBD-ABNT2", "TPD-001", "BAT-45WH", "PSU-65W", "CHS-001", "COOL-001", "BOX-001", "MAN-001", "LBL-001"]
MODELOS = [  # nome, código, meta, lista de componentes (sku, qtd)
    ("AMT N14", "N14-I5-8-256", 600, [(s, 1) for s in _BASE] + [("CPU-I5-12", 1), ("RAM-8G-D4", 1), ("SSD-256-NV", 1), ("LCD-14-FHD", 1)]),
    ("AMT N15", "N15-I5-8-512", 500, [(s, 1) for s in _BASE] + [("CPU-I5-12", 1), ("RAM-8G-D4", 1), ("SSD-512-NV", 1), ("LCD-156-FHD", 1)]),
    ("AMT N16", "N16-I7-16-512", 400, [(s, 1) for s in _BASE] + [("CPU-I7-13", 1), ("RAM-8G-D4", 2), ("SSD-512-NV", 1), ("LCD-156-FHD", 1)]),
    ("AMT N17", "N17-I7-16-512", 300, [(s, 1) for s in _BASE] + [("CPU-I7-13", 1), ("RAM-16G-D4", 1), ("SSD-512-NV", 1), ("LCD-14-FHD", 1)]),
    ("AMT N18", "N18-I5-16-256", 200, [(s, 1) for s in _BASE] + [("CPU-I5-12", 1), ("RAM-16G-D4", 1), ("SSD-256-NV", 1), ("LCD-156-FHD", 1)]),
]

FALHAS = [("Teclas do teclado não respondem no teste funcional", "Falha no teclado"),
          ("Tela com pixels mortos na inspeção", "Defeito de tela"),
          ("Wi-Fi não conecta durante o teste", "Falha no módulo Wi-Fi"),
          ("Bateria não carrega acima de 80%", "Bateria fora de especificação")]

_FLUXO = ["Em Fila", "Em Montagem", "Em Teste", "Aprovado", "Embalagem", "Expedição"]
_RETRABALHO = ["Em Fila", "Em Montagem", "Em Teste", "Reprovado", "Em Montagem", "Em Teste", "Aprovado", "Embalagem", "Expedição"]


def _caminho(i: int) -> list[str]:
    """Etapas por onde a produção i passou (o mesmo desenho do seed antigo)."""
    if i in (4, 8):
        return _RETRABALHO
    if i <= 10:
        return _FLUXO
    if i <= 16:
        return _FLUXO[: (5, 5, 4, 4, 3, 3)[i - 11]]
    if i <= 22:
        return _FLUXO[:2]
    return {23: ["Em Fila", "Em Montagem", "Parado"], 24: ["Em Fila", "Em Montagem", "Em Teste", "Reprovado"]}.get(i, ["Em Fila"])


def popular(sessao: Session, pessoas: dict[str, Usuario]) -> list[str]:
    """Povoa o schema ras se estiver vazio. `pessoas`: operador, operador2, inspetor, almoxarife."""
    feito = []
    if not sessao.scalar(select(Etapa.id).limit(1)):
        sessao.add_all(Etapa(nome=nome, ordem=ordem) for nome, ordem in ETAPAS_PADRAO)
        feito.append(f"ras.etapas: {len(ETAPAS_PADRAO)} etapas")
    if sessao.scalar(select(Componente.id).limit(1)):
        sessao.flush()
        return feito

    componentes = {sku: Componente(sku=sku, nome=nome, estoque=estoque) for sku, nome, estoque in COMPONENTES}
    sessao.add_all(componentes.values())
    modelos = []
    for nome, codigo, meta, lista in MODELOS:
        m = Modelo(codigo=codigo, nome=nome, meta=meta)
        m.componentes = [ModeloComponente(componente=componentes[sku], quantidade=q) for sku, q in lista]
        modelos.append(m)
    sessao.add_all(modelos)
    sessao.flush()
    etapa = {e.nome: e for e in sessao.scalars(select(Etapa))}

    rnd = random.Random(42)
    agora = tempo.agora()
    operadores = [pessoas["operador"], pessoas["operador2"]]
    inspetor, almox = pessoas["inspetor"], pessoas["almoxarife"]
    for i in range(1, 31):
        inicio = agora - timedelta(days=6 - (i - 1) * 7 // 30, minutes=(31 - i) * 9)
        caminho = _caminho(i)
        resp = operadores[i % 2]
        serie = f"{PREFIXO_SERIE}-{i:06d}"
        p = Producao(numero_serie=serie, id_unica=f"PRD-{serie}-{inicio.astimezone(tempo.FUSO_FABRICA):%Y%m%d}",
                     modelo=modelos[(i - 1) % len(modelos)], etapa=etapa[caminho[-1]], responsavel_id=resp.id,
                     criado_por_id=resp.id, iniciada_em=inicio, atualizada_em=inicio)
        sessao.add(p)
        sessao.flush()
        momento = inicio
        for nome in caminho:
            if nome != "Em Fila":
                momento = min(momento + timedelta(minutes=rnd.randint(25, 90)), agora - timedelta(minutes=1))
            quem = inspetor if nome in ("Em Teste", "Aprovado", "Reprovado") else resp
            origem = "MAQUINA/IOT" if nome == "Em Teste" and i % 3 == 0 else "MANUAL"
            sessao.add(Passagem(producao_id=p.id, etapa_id=etapa[nome].id, usuario_id=quem.id, responsavel_id=quem.id,
                                registrada_em=momento, origem=origem))
            if nome == "Reprovado":
                falha, motivo = FALHAS[(i + len(caminho)) % len(FALHAS)]
                sessao.add(NaoConformidade(producao_id=p.id, usuario_id=inspetor.id, descricao_falha=falha,
                                           motivo_reprovacao=motivo, registrada_em=momento))
        p.atualizada_em = momento
        p.responsavel_id = (inspetor if caminho[-1] in ("Em Teste", "Aprovado", "Reprovado") else resp).id

        # Materiais: as 25 primeiras pedem a lista do modelo; 17 a 22 ficam com baixa parcial (pendências).
        if i > 25:
            continue
        for k, item in enumerate(sorted(p.modelo.componentes, key=lambda x: x.componente_id)):
            completa = i <= 16 or (17 <= i <= 22 and k % 2 == 0)
            s = Solicitacao(producao_id=p.id, componente_id=item.componente_id, quantidade=item.quantidade,
                            status=(StatusSolicitacao.ATENDIDA if completa else StatusSolicitacao.PENDENTE).value,
                            criado_por_id=operadores[0].id, criada_em=inicio + timedelta(minutes=5))
            sessao.add(s)
            if completa:
                sessao.flush()
                sessao.add(Baixa(solicitacao_id=s.id, usuario_id=almox.id, quantidade=item.quantidade,
                                 registrada_em=inicio + timedelta(minutes=20)))
                item.componente.estoque -= item.quantidade

    # Alertas de estoque crítico e de pendência maior que o estoque, como no sistema antigo.
    componentes["BAT-45WH"].estoque = 4
    componentes["LCD-156-FHD"].estoque = 38
    sessao.flush()
    feito += [f"ras.componentes: {len(COMPONENTES)} componentes", f"ras.modelos: {len(MODELOS)} modelos com a lista de componentes",
              "ras.producoes: 30 produções (AMT-000001 a AMT-000030) com histórico e materiais"]
    return feito
