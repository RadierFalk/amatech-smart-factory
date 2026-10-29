"""Fórmulas dos indicadores e semáforo, com os casos de referência do enunciado (testes/README.md).

O script do banco já traz o exemplo: 15/08/2026, 1º turno, modelo A, meta 1.500, 1.420 produzidos,
1.360 aprovados, 60 reprovados, 30 em retrabalho e 85 min de parada no Testador 02.
"""
from datetime import date, datetime

import pytest

from servicos.alertas import AvaliadorAlertas
from servicos.calculadora import CalculadoraIndicadores
from servicos.erros import ErroValidacao
from servicos.filtro import Filtro
from servicos.registro import ServicoRegistro

DIA = date(2026, 8, 15)


@pytest.fixture
def resultado(repo):
    return CalculadoraIndicadores(repo).calcular(Filtro(DIA, DIA))


def test_atendimento_da_meta(resultado):
    assert round(resultado.atendimento_meta, 1) == 94.7


def test_indice_de_defeitos(resultado):
    assert round(resultado.indice_defeitos, 1) == 4.2


def test_indice_de_retrabalho(resultado):
    assert round(resultado.indice_retrabalho, 1) == 2.1


def test_produtividade_desconta_as_paradas(resultado):
    assert resultado.minutos_produtivos == 395
    assert round(resultado.produtividade, 1) == 215.7


def test_tempo_de_parada(resultado):
    assert resultado.tempo_parada.minutos == 85
    assert resultado.tempo_parada.encerradas == 1


def test_semaforo_do_exemplo_fica_amarelo(repo, resultado):
    alertas = AvaliadorAlertas(repo)
    assert alertas.classificar("atendimento_meta", resultado.atendimento_meta) == "amarelo"
    assert alertas.classificar("indice_defeitos", resultado.indice_defeitos) == "amarelo"


@pytest.mark.parametrize("indicador, valor, cor", [
    ("atendimento_meta", 95, "verde"), ("atendimento_meta", 74.9, "vermelho"),
    ("indice_defeitos", 2, "verde"), ("indice_defeitos", 5.1, "vermelho"),
    ("atendimento_meta", None, None),   # sem meta: sem cor (RN03)
])
def test_limites_do_semaforo(repo, indicador, valor, cor):
    assert AvaliadorAlertas(repo).classificar(indicador, valor) == cor


def test_limites_incoerentes_sao_recusados(repo):
    with pytest.raises(ErroValidacao):
        AvaliadorAlertas(repo).salvar_limites("atendimento_meta", 70, 80)   # maior é melhor: amarelo < verde
    AvaliadorAlertas(repo).salvar_limites("atendimento_meta", 90, 70)
    assert AvaliadorAlertas(repo).classificar("atendimento_meta", 94.7) == "verde"


def test_sem_meta_nao_ha_atendimento(repo):
    resultado = CalculadoraIndicadores(repo).calcular(Filtro(date(2026, 8, 16), date(2026, 8, 16)))
    assert resultado.atendimento_meta is None and not resultado.tem_dados


def test_parada_em_andamento_conta_ate_agora(repo, supervisor, monkeypatch):
    monkeypatch.setattr("config.agora", lambda: datetime(2026, 8, 15, 12, 0))
    ServicoRegistro(repo).registrar_parada(1, 1, 3, "2026-08-15 11:30", supervisor)   # sem fim
    tempo = CalculadoraIndicadores(repo).tempo_parada(Filtro(DIA, DIA))
    assert tempo.minutos == 85 + 30 and tempo.em_andamento == 1


@pytest.mark.parametrize("inicio, fim", [(date(2026, 8, 15), date(2026, 8, 14)),
                                         (date(2025, 1, 1), date(2026, 8, 15))])
def test_periodo_invalido_e_recusado(inicio, fim):
    with pytest.raises(ErroValidacao):
        Filtro(inicio, fim).validar()   # RN05: período fechado de até 366 dias
