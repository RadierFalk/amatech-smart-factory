"""Regras de negócio do ServicoRegistro, dos cadastros e da autenticação."""
from datetime import date, datetime

import pytest

from servicos.autenticacao import ServicoAutenticacao
from servicos.cadastros import ServicoCadastros
from servicos.erros import ErroValidacao
from servicos.registro import ServicoRegistro


def contar(repo, tabela):
    return repo.consultar_um(f"SELECT COUNT(*) AS n FROM {tabela}")["n"]


def test_aprovados_mais_reprovados_diferente_do_realizado_e_recusado(repo, supervisor):
    with pytest.raises(ErroValidacao) as erro:
        ServicoRegistro(repo).registrar_producao(date(2026, 8, 16), 1, 1, 100, 90, 5, supervisor)
    assert erro.value.problemas[0][0] == "qtd_reprovada"
    assert contar(repo, "registro_producao") == 1   # só o exemplo do script


def test_meta_duplicada_e_recusada(repo, supervisor):
    with pytest.raises(ErroValidacao, match="RN09"):
        ServicoRegistro(repo).registrar_meta(date(2026, 8, 15), 1, 1, 1000, supervisor)


def test_retrabalho_exige_motivo(repo, supervisor):
    with pytest.raises(ErroValidacao, match="RN02"):
        ServicoRegistro(repo).registrar_retrabalho(1, 3, "  ", 5, datetime(2026, 8, 15, 10, 0), supervisor)


def test_parada_com_fim_antes_do_inicio_e_recusada(repo, supervisor):
    with pytest.raises(ErroValidacao):
        ServicoRegistro(repo).registrar_parada(1, 1, 1, "15/08/2026 10:00", supervisor, fim="15/08/2026 09:00")


def test_encerrar_parada(repo, supervisor):
    registro = ServicoRegistro(repo)
    id_parada = registro.registrar_parada(1, 1, 3, "2026-08-15 11:00", supervisor)
    registro.encerrar_parada(id_parada, "2026-08-15 11:20")
    with pytest.raises(ErroValidacao, match="já foi encerrada"):
        registro.encerrar_parada(id_parada, "2026-08-15 11:30")


def test_registro_externo_e_atualizado_e_nao_duplicado(repo, supervisor):
    """Sincronizar de novo com outro setor atualiza o registro (origem_sistema + id_externo)."""
    registro = ServicoRegistro(repo)
    externo = {"origem_sistema": "manutencao", "id_externo": "MNT-7"}
    primeiro = registro.registrar_parada(4, 1, 1, "2026-08-15 08:00", supervisor, **externo)
    segundo = registro.registrar_parada(4, 1, 1, "2026-08-15 08:00", supervisor, fim="2026-08-15 08:40", **externo)
    assert primeiro == segundo
    assert repo.consultar_um("SELECT fim FROM parada WHERE id_parada = ?", (primeiro,))["fim"] == "2026-08-15 08:40"


def test_nomes_dos_outros_setores_sao_reconhecidos(repo):
    cadastros = ServicoCadastros(repo)
    assert cadastros.buscar_id("estacao", "SMT") == cadastros.buscar_id("estacao", "Linha SMT")
    assert cadastros.buscar_id("estacao", "INSPEÇÃO DE QUALIDADE") == cadastros.buscar_id("estacao",
                                                                                           "Inspeção da qualidade")
    assert cadastros.buscar_id("turno", "1") == cadastros.buscar_id("turno", "1º turno")
    assert cadastros.buscar_id("estacao", "Pintura") is None


def test_turno_pelo_horario(repo):
    cadastros = ServicoCadastros(repo)
    assert cadastros.turno_por_horario(datetime(2026, 8, 15, 9, 30))["nome"] == "1º turno"
    assert cadastros.turno_por_horario(datetime(2026, 8, 15, 14, 0))["nome"] == "2º turno"
    assert cadastros.turno_por_horario(datetime(2026, 8, 15, 23, 0)) is None


def test_login_e_permissoes(repo):
    auth = ServicoAutenticacao(repo)
    assert auth.autenticar("supervisor", "errada") is None
    supervisor = auth.autenticar("Supervisor ", "super123")
    assert supervisor.nome == "Maria Souza"
    assert auth.tem_permissao(supervisor, "importacao")
    assert not auth.tem_permissao(supervisor, "usuarios")
    assert not auth.tem_permissao(auth.autenticar("gestor", "gestor123"), "producao")


def test_usuario_desativado_nao_entra(repo):
    auth = ServicoAutenticacao(repo)
    id_usuario = auth.criar_usuario("Ana Costa", "ana", 2, "senha123")
    assert auth.autenticar("ana", "senha123") is not None
    auth.alterar_ativo(id_usuario, False)
    assert auth.autenticar("ana", "senha123") is None


def test_senha_guardada_com_hash_e_sal():
    h1, h2 = ServicoAutenticacao.gerar_hash("segredo1"), ServicoAutenticacao.gerar_hash("segredo1")
    assert h1 != h2 and "segredo1" not in h1
    assert ServicoAutenticacao.conferir_senha("segredo1", h1)
    assert not ServicoAutenticacao.conferir_senha("segredo2", h1)
