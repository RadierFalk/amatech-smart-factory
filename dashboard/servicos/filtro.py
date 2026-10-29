"""Classe Filtro: período, turno e produto escolhidos no painel e no histórico (RF12, RN05)."""
from dataclasses import dataclass
from datetime import date

from servicos.erros import ErroValidacao

MAXIMO_DIAS = 366


@dataclass
class Filtro:
    data_inicial: date
    data_final: date
    id_turno: int | None = None      # None = todos os turnos
    id_produto: int | None = None    # None = todos os produtos

    def validar(self):
        """RN05: todo indicador é calculado para um período fechado, nunca acumulado indefinidamente."""
        if self.data_inicial is None or self.data_final is None:
            raise ErroValidacao("Informe a data inicial e a data final.")
        if self.data_final < self.data_inicial:
            raise ErroValidacao("A data final não pode ser anterior à data inicial.")
        if (self.data_final - self.data_inicial).days >= MAXIMO_DIAS:
            raise ErroValidacao(f"Escolha um período de até {MAXIMO_DIAS} dias.")
        return self

    @property
    def dias(self):
        return (self.data_final - self.data_inicial).days + 1
