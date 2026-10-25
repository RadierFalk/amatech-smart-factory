"""Migrações do banco: aplica somente o que ainda não foi aplicado e NUNCA apaga tabelas existentes.
Assim o sistema pode ser ligado a um banco compartilhado com as outras equipes."""
from app import config

# Tabelas deste sistema e as colunas que o código usa. Se o banco compartilhado já tiver uma tabela com o
# mesmo nome mas sem essas colunas, o sistema avisa em vez de falhar no meio do uso.
COLUNAS_OBRIGATORIAS = {
    "usuarios": {"id", "matricula", "nome", "email", "senha_hash", "cargo", "ativo", "criado_por", "criado_em"},
    "status_producao": {"id", "nome_status", "ordem", "criado_por", "criado_em"},
    "produtos": {"idprd", "nome_modelo", "codigo_modelo", "quantidade", "criado_por", "criado_em"},
    "componentes": {"idcmp", "nome", "codigo_sku", "qtd_estoque", "criado_por", "criado_em"},
    "produto_componentes": {"produto_id", "componente_id", "quantidade_necessaria", "criado_por", "criado_em"},
    "producoes": {"id", "numero_serie_notebook", "id_unica_producao", "produto_id", "status_atual_id", "data_inicio",
                  "responsavel_etapa_id", "criado_por", "criado_em"},
    "historico_passagem": {"id", "producao_id", "status_id", "usuario_id", "responsavel_etapa_id", "data_horario",
                           "origem_atualizacao"},
    "nao_conformidades": {"id", "producao_id", "usuario_id", "descricao_falha", "motivo_reprovacao", "data_registro"},
    "solicitacoes_materiais": {"id", "producao_id", "componente_id", "quantidade_solicitada", "status_solicitacao",
                               "criado_por", "criado_em"},
    "baixas_materiais": {"id", "solicitacao_id", "usuario_id", "quantidade_baixada", "data_baixa"},
}


def colunas_da_tabela(conn, tabela):
    return {linha[1] for linha in conn.execute(f"PRAGMA table_info({tabela})")}


def verificar_compatibilidade(conn):
    """Se uma tabela com o mesmo nome já existe (criada por outra equipe), confere se tem as colunas necessárias."""
    problemas = []
    for tabela, obrigatorias in COLUNAS_OBRIGATORIAS.items():
        existentes = colunas_da_tabela(conn, tabela)
        if existentes and not obrigatorias <= existentes:
            problemas.append(f"  - tabela '{tabela}': faltam as colunas {sorted(obrigatorias - existentes)}")
    if problemas:
        raise RuntimeError(
            "O banco já possui tabelas com o mesmo nome do sistema de Rastreabilidade, mas com colunas diferentes:\n"
            + "\n".join(problemas)
            + "\nResolva o conflito com a outra equipe (veja docs/INTEGRACAO.md e rode "
              "python tools/verificar_conflitos.py <outro_banco.db>) antes de iniciar o sistema.")


def aplicar(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS _migracoes (versao INTEGER PRIMARY KEY, nome TEXT NOT NULL, "
                 "aplicada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    aplicadas = {linha[0] for linha in conn.execute("SELECT versao FROM _migracoes")}
    for arquivo in sorted(config.MIGRACOES_DIR.glob("*.sql")):
        versao = int(arquivo.name.split("_")[0])
        if versao in aplicadas:
            continue
        if versao == 1:
            verificar_compatibilidade(conn)
        conn.executescript(arquivo.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO _migracoes (versao, nome) VALUES (?, ?)", (versao, arquivo.name))
        conn.commit()
