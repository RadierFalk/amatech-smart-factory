"""Compara o banco de OUTRA equipe com o esquema deste sistema, antes de unir os bancos.

Uso (na pasta do projeto):
    python tools/verificar_conflitos.py caminho/para/banco_da_outra_equipe.db

O que o script mostra:
  1. Tabelas com o MESMO NOME nos dois bancos (conflito em potencial) e a diferença de colunas.
  2. Tabelas que existem só no banco da outra equipe (não geram conflito, serão apenas "somadas").
  3. Chaves estrangeiras da outra equipe que apontam para tabelas deste sistema (pontos de integração).
O banco da outra equipe é aberto SOMENTE LEITURA — nada é alterado.
"""
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from app import config, migracoes  # noqa: E402


def esquema(conn):
    """{tabela: {coluna: tipo}} ignorando tabelas internas do SQLite e de controle."""
    saida = {}
    tabelas = conn.execute("SELECT name FROM sqlite_master WHERE type='table' "
                           "AND name NOT LIKE 'sqlite_%' AND name != '_migracoes'").fetchall()
    for (nome,) in tabelas:
        saida[nome] = {c[1]: (c[2] or "").upper() for c in conn.execute(f"PRAGMA table_info({nome})")}
    return saida


def esquema_deste_sistema():
    conn = sqlite3.connect(":memory:")
    for arquivo in sorted(config.MIGRACOES_DIR.glob("*.sql")):
        conn.executescript(arquivo.read_text(encoding="utf-8"))
    return esquema(conn)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    caminho = Path(sys.argv[1])
    if not caminho.exists():
        print(f"Arquivo não encontrado: {caminho}")
        return 2
    outro_conn = sqlite3.connect(f"file:{caminho.resolve().as_posix()}?mode=ro", uri=True)
    meu, outro = esquema_deste_sistema(), esquema(outro_conn)

    comuns = sorted(set(meu) & set(outro))
    so_outro = sorted(set(outro) - set(meu))
    conflitos = 0

    print(f"Banco analisado: {caminho}\n")
    print("== 1) Tabelas com o mesmo nome ==")
    if not comuns:
        print("  Nenhuma. Os dois bancos podem ser unidos sem conflito de nomes.")
    for t in comuns:
        faltam_la = sorted(set(meu[t]) - set(outro[t]))   # colunas que o nosso sistema usa e a outra tabela não tem
        extras_la = sorted(set(outro[t]) - set(meu[t]))
        tipos = [c for c in meu[t] if c in outro[t] and meu[t][c] != outro[t][c]]
        obrig = migracoes.COLUNAS_OBRIGATORIAS.get(t, set())
        grave = sorted(obrig - set(outro[t]))
        if not (faltam_la or extras_la or tipos):
            print(f"  [OK]       {t}: estrutura idêntica (podem compartilhar a tabela).")
            continue
        conflitos += 1 if grave else 0
        print(f"  [{'CONFLITO' if grave else 'ATENÇÃO '}] {t}")
        if grave:
            print(f"       colunas que o nosso sistema EXIGE e a outra tabela não tem: {grave}")
        if faltam_la and not grave:
            print(f"       colunas nossas ausentes lá (opcionais): {faltam_la}")
        if extras_la:
            print(f"       colunas extras lá (o nosso sistema ignora): {extras_la}")
        if tipos:
            print(f"       tipos diferentes: " + ", ".join(f"{c} ({meu[t][c]} x {outro[t][c]})" for c in tipos))

    print("\n== 2) Tabelas só do outro banco (serão apenas adicionadas) ==")
    print("  " + (", ".join(so_outro) if so_outro else "nenhuma"))

    print("\n== 3) Pontos de integração (FKs deles apontando para tabelas nossas) ==")
    achou = False
    for t in so_outro:
        for fk in outro_conn.execute(f"PRAGMA foreign_key_list({t})"):
            if fk[2] in meu:
                achou = True
                print(f"  {t}.{fk[3]} -> {fk[2]}.{fk[4]}")
    if not achou:
        print("  Nenhuma FK declarada. Se vão se relacionar, combinem as colunas (ex.: producoes.numero_serie_notebook).")

    print("\n== Resultado ==")
    if conflitos:
        print(f"  {conflitos} conflito(s) grave(s). Combinem com a outra equipe quem é dono da tabela "
              "(veja docs/INTEGRACAO.md, seção 'Conflitos').")
        return 1
    print("  Sem conflitos graves. Pode seguir o passo a passo de união em docs/INTEGRACAO.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
