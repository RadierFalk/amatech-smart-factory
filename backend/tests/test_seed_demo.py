"""A carga de demonstração (usada por iniciar-demo e AMATECH_SEED_DEMO=1) povoa todos os módulos e não repete."""
from sqlalchemy import func, select

from app.modulos.dashboard.modelos import Meta
from app.modulos.manutencao.modelos import Chamado, Equipamento
from app.modulos.qualidade.modelos import Ocorrencia
from app.modulos.rastreabilidade.modelos import Producao
from app.modulos.usuarios.modelos import Usuario
from scripts import seed_demo


def contar(sessao, modelo) -> int:
    return sessao.scalar(select(func.count()).select_from(modelo))


def test_demo_povoa_todos_os_modulos_uma_vez(sessao):
    seed_demo.popular(sessao)
    sessao.commit()

    assert contar(sessao, Usuario) >= len(seed_demo.PERSONAS)
    assert contar(sessao, Producao) > 0
    assert contar(sessao, Meta) > 0
    assert contar(sessao, Chamado) > 0
    assert contar(sessao, Ocorrencia) > 0
    # Uma máquina parada com chamado em andamento, para o aviso do Dashboard aparecer.
    assert sessao.scalar(select(Equipamento.status_operacional).where(Equipamento.codigo_tag == "TEST-02")) == "PARADA"
    assert sessao.scalar(select(func.count()).select_from(Chamado).where(Chamado.status_chamado == "EM_ANDAMENTO")) == 1

    antes = (contar(sessao, Chamado), contar(sessao, Ocorrencia), contar(sessao, Producao))
    assert seed_demo.popular(sessao) == []  # tudo já povoado: nada a fazer
    assert (contar(sessao, Chamado), contar(sessao, Ocorrencia), contar(sessao, Producao)) == antes
