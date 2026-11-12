"""Importa os modelos de todos os módulos para registrá-los no Base.metadata.

Usado pelo Alembic e pelos testes. Ao criar os modelos de um módulo novo, importe-os aqui.
"""
from app.modulos.manutencao.modelos import Chamado, ChamadoPeca, Equipamento, HistoricoStatus, Peca
from app.modulos.qualidade.modelos import Estacao, Ocorrencia, Produto, TipoDefeito
from app.modulos.usuarios.modelos import Usuario

__all__ = [
    "Chamado", "ChamadoPeca", "Equipamento", "Estacao", "HistoricoStatus", "Ocorrencia", "Peca", "Produto",
    "TipoDefeito", "Usuario",
]
