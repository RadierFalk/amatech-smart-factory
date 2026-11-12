"""Indicadores da Qualidade (portado de qualidade/indicadores.py e graficos.py).

Contam só as ocorrências visíveis. O dia de cada ocorrência é o dia da fábrica (Manaus).
"""
from collections import Counter
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.core import tempo
from app.modulos.qualidade import servico
from app.modulos.qualidade.constantes import Classificacao, SituacaoProduto, StatusOcorrencia


def _contagem(valores) -> list[dict[str, Any]]:
    """[{rotulo, ocorrencias}] do maior para o menor (empate: ordem alfabética)."""
    return [{"rotulo": r, "ocorrencias": n} for r, n in sorted(Counter(valores).items(), key=lambda x: (-x[1], x[0]))]


def indicadores(sessao: Session, de: date | None = None, ate: date | None = None) -> dict[str, Any]:
    ocorrencias = servico.listar(sessao, de=de, ate=ate, limite=100_000)
    por_estacao = _contagem(o.estacao.nome for o in ocorrencias)
    por_dia = Counter(tempo.utc(o.ocorrida_em).astimezone(tempo.FUSO_FABRICA).date().isoformat() for o in ocorrencias)
    return {
        "total_ocorrencias": len(ocorrencias),
        "ocorrencias_abertas": sum(o.status == StatusOcorrencia.ABERTA for o in ocorrencias),
        "ocorrencias_em_analise": sum(o.status == StatusOcorrencia.EM_ANALISE for o in ocorrencias),
        "produtos_reprovados": len(
            {o.produto_id for o in ocorrencias if o.situacao_produto == SituacaoProduto.REPROVADO}
        ),
        "criticas": sum(o.classificacao == Classificacao.CRITICO for o in ocorrencias),
        "estacao_critica": por_estacao[0]["rotulo"] if por_estacao else None,
        "por_tipo_defeito": _contagem(o.tipo_defeito.nome for o in ocorrencias),
        "por_estacao": por_estacao,
        "por_maquina": _contagem(o.equipamento.codigo_tag for o in ocorrencias),
        "por_classificacao": _contagem(o.classificacao for o in ocorrencias),
        "por_dia": [{"data": d, "ocorrencias": n} for d, n in sorted(por_dia.items())],
    }
