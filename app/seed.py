"""Cria o banco SQLite com dados SIMULADOS de demonstração (permitido pelo enunciado, item 2.8).

Uso:  python -m app.seed            -> recria o banco do zero
"""
import random
from datetime import datetime, timedelta, timezone

from app import config, migracoes
from app.db import conectar
from app.seguranca import hash_senha
from app.servicos import materiais

SENHA_DEMO = "amatech123"

USUARIOS = [  # matrícula, nome, e-mail, cargo
    ("MAT-0001", "Administrador do Sistema", "admin@amatech.com.br", "Administrador"),
    ("MAT-00421", "Carlos Mendonça", "carlos.mendonca@amatech.com.br", "Operador"),
    ("MAT-00422", "Juliana Ferreira", "juliana.ferreira@amatech.com.br", "Operador"),
    ("MAT-0100", "Ana Beatriz Souza", "ana.souza@amatech.com.br", "Almoxarife"),
    ("MAT-0200", "Rafael Lima", "rafael.lima@amatech.com.br", "Inspetor de Qualidade"),
]

STATUS = [("Em Fila", 1), ("Em Montagem", 2), ("Em Teste", 3), ("Aprovado", 4), ("Embalagem", 5),
          ("Expedição", 6), ("Parado", 90), ("Reprovado", 91)]

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

_BASE = ["PCB-MB-001", "KBD-ABNT2", "TPD-001", "BAT-45WH", "PSU-65W", "CHS-001", "COOL-001",
         "BOX-001", "MAN-001", "LBL-001"]
PRODUTOS = [  # nome, código, meta, lista de componentes (sku, qtd)
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


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def recriar_banco():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    for sufixo in ("", "-wal", "-shm", "-journal"):
        arquivo = config.DB_PATH.with_name(config.DB_PATH.name + sufixo)
        if arquivo.exists():
            arquivo.unlink()
    conn = conectar()
    migracoes.aplicar(conn)
    popular(conn)
    conn.close()


def popular(conn):
    rnd = random.Random(42)
    agora = datetime.now(timezone.utc)
    senha = hash_senha(SENHA_DEMO)

    # ---- usuários (o administrador é o primeiro; os demais são "criados por" ele)
    ids = {}
    for i, (mat, nome, email, cargo) in enumerate(USUARIOS):
        cur = conn.execute("INSERT INTO usuarios (matricula, nome, email, senha_hash, cargo, criado_por) VALUES (?,?,?,?,?,?)",
                           (mat, nome, email, senha, cargo, None if i == 0 else 1))
        ids[mat] = cur.lastrowid
    # usuário de serviço da integração com máquinas (não faz login: hash inválido e inativo)
    conn.execute("INSERT INTO usuarios (matricula, nome, email, senha_hash, cargo, ativo, criado_por) VALUES (?,?,?,?,?,0,1)",
                 (config.MATRICULA_IOT, "Integração (máquinas e sistemas externos)", "iot@amatech.com.br", "!", "Integração"))
    admin = ids["MAT-0001"]
    operadores = [ids["MAT-00421"], ids["MAT-00422"]]
    inspetor, almox = ids["MAT-0200"], ids["MAT-0100"]

    # ---- status, componentes, produtos e lista de componentes
    st = {}
    for nome, ordem in STATUS:
        st[nome] = conn.execute("INSERT INTO status_producao (nome_status, ordem, criado_por) VALUES (?,?,?)",
                                (nome, ordem, admin)).lastrowid
    cmp_id = {}
    for sku, nome, estoque in COMPONENTES:
        cmp_id[sku] = conn.execute("INSERT INTO componentes (nome, codigo_sku, qtd_estoque, criado_por) VALUES (?,?,?,?)",
                                   (nome, sku, estoque, admin)).lastrowid
    prod_ids = []
    for nome, codigo, meta, lista in PRODUTOS:
        pid = conn.execute("INSERT INTO produtos (nome_modelo, codigo_modelo, quantidade, criado_por) VALUES (?,?,?,?)",
                           (nome, codigo, meta, admin)).lastrowid
        prod_ids.append(pid)
        for sku, qtd in lista:
            conn.execute("INSERT INTO produto_componentes (produto_id, componente_id, quantidade_necessaria, criado_por) "
                         "VALUES (?,?,?,?)", (pid, cmp_id[sku], qtd, admin))

    # ---- produções simuladas (AMT-000001 ... AMT-000030) com histórico de passagem
    fluxo = ["Em Fila", "Em Montagem", "Em Teste", "Aprovado", "Embalagem", "Expedição"]
    destino = {}                                   # nº -> caminho de etapas
    for i in range(1, 11):
        destino[i] = fluxo[:]                       # concluídas (Expedição)
    destino[4] = ["Em Fila", "Em Montagem", "Em Teste", "Reprovado", "Em Montagem", "Em Teste", "Aprovado", "Embalagem", "Expedição"]
    destino[8] = ["Em Fila", "Em Montagem", "Em Teste", "Reprovado", "Em Montagem", "Em Teste", "Aprovado", "Embalagem", "Expedição"]
    for i, ate in zip(range(11, 17), (5, 5, 4, 4, 3, 3)):
        destino[i] = fluxo[:ate]                    # Embalagem, Aprovado, Em Teste
    for i in range(17, 23):
        destino[i] = fluxo[:2]                      # Em Montagem
    destino[23] = ["Em Fila", "Em Montagem", "Parado"]
    destino[24] = ["Em Fila", "Em Montagem", "Em Teste", "Reprovado"]
    for i in range(25, 31):
        destino[i] = ["Em Fila"]

    inicio = {}
    for i in range(1, 31):
        dia = 6 - (i - 1) * 7 // 30   # espalha as 30 produções pelos últimos 7 dias
        t = agora - timedelta(days=dia, minutes=(31 - i) * 9)
        inicio[i] = t
        pid = prod_ids[(i - 1) % len(prod_ids)]
        resp = operadores[i % 2]
        serie = f"{config.PREFIXO_SERIE}-{i:06d}"
        id_unica = f"PRD-{serie}-{t.astimezone(timezone(timedelta(hours=config.FUSO_HORAS))):%Y%m%d}"
        caminho = destino[i]
        conn.execute("INSERT INTO producoes (id, numero_serie_notebook, id_unica_producao, produto_id, status_atual_id, "
                     "data_inicio, responsavel_etapa_id, criado_por, criado_em) VALUES (?,?,?,?,?,?,?,?,?)",
                     (i, serie, id_unica, pid, st[caminho[-1]], _ts(t), resp, resp, _ts(t)))
        momento = t
        for etapa in caminho:
            if etapa != "Em Fila":
                momento = min(momento + timedelta(minutes=rnd.randint(25, 90)), agora - timedelta(minutes=1))
            quem = inspetor if etapa in ("Em Teste", "Aprovado", "Reprovado") else resp
            conn.execute("INSERT INTO historico_passagem (producao_id, status_id, usuario_id, responsavel_etapa_id, "
                         "data_horario, origem_atualizacao) VALUES (?,?,?,?,?,?)",
                         (i, st[etapa], quem, quem, _ts(momento), "MAQUINA/IOT" if etapa == "Em Teste" and i % 3 == 0 else "MANUAL"))
            if etapa == "Reprovado":
                falha, motivo = FALHAS[(i + len(caminho)) % len(FALHAS)]
                conn.execute("INSERT INTO nao_conformidades (producao_id, usuario_id, descricao_falha, motivo_reprovacao, "
                             "data_registro) VALUES (?,?,?,?,?)", (i, inspetor, falha, motivo, _ts(momento)))
        conn.execute("UPDATE producoes SET responsavel_etapa_id = ? WHERE id = ?",
                     (inspetor if caminho[-1] in ("Em Teste", "Aprovado", "Reprovado") else resp, i))
    conn.commit()

    # ---- fluxo de materiais: solicitações pela lista do produto e baixas pelo almoxarife
    solicitante = {"id": operadores[0], "nome": "seed"}
    baixador = {"id": almox, "nome": "seed"}
    for i in range(1, 26):
        materiais.gerar_solicitacoes_da_producao(conn, i, solicitante)
        itens = materiais.listar_solicitacoes(conn, producao_id=i)
        for k, s in enumerate(sorted(itens, key=lambda x: x["id"])):
            if i <= 16 or (17 <= i <= 22 and k % 2 == 0):   # as 17-22 ficam com baixa parcial (pendências)
                materiais.criar_baixa(conn, s["id"], s["quantidade_solicitada"], baixador)
        conn.execute("UPDATE solicitacoes_materiais SET criado_em = ? WHERE producao_id = ?",
                     (_ts(inicio[i] + timedelta(minutes=5)), i))
        conn.execute("UPDATE baixas_materiais SET data_baixa = ? WHERE solicitacao_id IN "
                     "(SELECT id FROM solicitacoes_materiais WHERE producao_id = ?)", (_ts(inicio[i] + timedelta(minutes=20)), i))
    # ajustes de inventário para demonstrar alertas de estoque crítico e pendência maior que o estoque
    conn.execute("UPDATE componentes SET qtd_estoque = 4 WHERE codigo_sku = 'BAT-45WH'")
    conn.execute("UPDATE componentes SET qtd_estoque = 38 WHERE codigo_sku = 'LCD-156-FHD'")
    conn.execute("DELETE FROM integracao_eventos")   # a fila de eventos começa limpa depois do povoamento
    conn.commit()


if __name__ == "__main__":
    recriar_banco()
    print("Banco criado em", config.DB_PATH)
