"""ImportadorCSV: tudo ou nada (RN06), mensagens por linha e coluna, formatos aceitos e entrada da sincronização."""
import pytest

from servicos.importador_csv import MODELOS, ImportadorCSV

CABECALHO = "data;turno;produto;qtd_realizada;qtd_aprovada;qtd_reprovada\n"


def contar(repo, tabela):
    return repo.consultar_um(f"SELECT COUNT(*) AS n FROM {tabela}")["n"]


@pytest.fixture
def importador(repo):
    return ImportadorCSV(repo)


def test_uma_linha_invalida_nao_grava_nada(repo, importador, supervisor):
    conteudo = (CABECALHO + "16/08/2026;1º turno;Notebook modelo A;100;90;10\n"
                          "16/08/2026;1º turno;Notebook modelo B;100;90;5\n").encode()
    resultado = importador.importar(conteudo, "producao", supervisor, "producao.csv")
    assert resultado.status == "rejeitada"
    assert resultado.erros == [(3, "qtd_reprovada", "Aprovados + reprovados diferente do realizado (RNF04).")]
    assert contar(repo, "registro_producao") == 1                  # só o exemplo do script
    historico = repo.consultar_um("SELECT * FROM importacao")      # a tentativa recusada fica registrada
    assert (historico["status"], historico["linhas_lidas"], historico["linhas_rejeitadas"]) == ("rejeitada", 2, 1)


def test_todos_os_erros_sao_listados(importador, supervisor):
    conteudo = (CABECALHO + "32/08/2026;3º turno;Notebook X;dez;90;10\n").encode()
    colunas = {coluna for _, coluna, _ in importador.importar(conteudo, "producao", supervisor, "x.csv").erros}
    assert colunas == {"data", "turno", "produto", "qtd_realizada"}


def test_importacao_valida_grava_e_registra(repo, importador, supervisor):
    conteudo = (CABECALHO + "16/08/2026;1;Notebook modelo A;100;90;10\n\n").encode()   # linha em branco é ignorada
    resultado = importador.importar(conteudo, "producao", supervisor, "producao.csv")
    assert (resultado.status, resultado.importadas) == ("concluida", 1)
    assert repo.consultar_um("SELECT id_importacao FROM registro_producao WHERE data = '2026-08-16'")[
        "id_importacao"] == resultado.id_importacao


def test_coluna_obrigatoria_ausente(importador, supervisor):
    resultado = importador.importar(b"data;turno\n16/08/2026;1\n", "producao", supervisor, "x.csv")
    assert resultado.status == "rejeitada"
    assert {(linha, coluna) for linha, coluna, _ in resultado.erros} == {
        (1, "produto"), (1, "qtd_realizada"), (1, "qtd_aprovada"), (1, "qtd_reprovada")}


def test_aceita_virgula_e_codificacao_do_excel(importador, supervisor):
    conteudo = ("Data,Turno,Produto,Qtd_Realizada,Qtd_Aprovada,Qtd_Reprovada\n"
                "16/08/2026,1º turno,Notebook modelo A,10,10,0\n").encode("cp1252")
    assert importador.importar(conteudo, "producao", supervisor, "x.csv").status == "concluida"


def test_validar_arquivo_nao_grava(repo, importador, supervisor):
    conteudo = (CABECALHO + "16/08/2026;1;Notebook modelo A;100;90;10\n").encode()
    assert importador.validar_arquivo(conteudo, "producao", supervisor).status == "valida"
    assert contar(repo, "registro_producao") == 1 and contar(repo, "importacao") == 0


def test_defeito_precisa_da_producao(importador, supervisor):
    conteudo = ("data;turno;produto;tipo_defeito;estacao;quantidade;data_hora\n"
                "01/01/2026;1;Notebook modelo A;Falha no teclado;Teste funcional;2;01/01/2026 08:00\n").encode()
    resultado = importador.importar(conteudo, "defeito", supervisor, "x.csv")
    assert resultado.erros[0][:2] == (2, "data")


@pytest.mark.parametrize("tipo", list(MODELOS))
def test_modelos_para_download_sao_importaveis(repo, importador, supervisor, tipo):
    importador.importar(ImportadorCSV.modelo_csv("producao"), "producao", supervisor, "p.csv")   # defeito precisa
    resultado = importador.importar(ImportadorCSV.modelo_csv(tipo), tipo, supervisor, f"modelo_{tipo}.csv")
    assert resultado.status == "concluida", resultado.erros


def test_defeito_com_retrabalho_e_sinonimos(repo, importador, supervisor):
    conteudo = ("data;turno;produto;tipo_defeito;estacao;quantidade;data_hora;estacao_retorno;"
                "motivo_retrabalho;qtd_retrabalho\n"
                "15/08/2026;1;Notebook modelo A;teclado;SMT;3;15/08/2026 11:00;Montagem final;Troca;3\n").encode()
    assert importador.importar(conteudo, "defeito", supervisor, "x.csv").status == "concluida"
    assert contar(repo, "retrabalho") == 2   # o do exemplo e o novo


def test_sincronizacao_atualiza_sem_duplicar(repo, importador, supervisor):
    linha = {"data": "2026-08-18", "turno": "1º turno", "produto": "Notebook modelo B", "qtd_realizada": 10,
             "qtd_aprovada": 9, "qtd_reprovada": 1, "origem_sistema": "rastreabilidade",
             "id_externo": "2026-08-18|1º turno|Notebook modelo B"}
    importador.importar_linhas([linha], "producao", supervisor, "sincronização")
    importador.importar_linhas([dict(linha, qtd_realizada=12, qtd_aprovada=11)], "producao", supervisor,
                               "sincronização")
    linhas = repo.consultar("SELECT qtd_realizada FROM registro_producao WHERE origem_sistema = 'rastreabilidade'")
    assert linhas == [{"qtd_realizada": 12}]
