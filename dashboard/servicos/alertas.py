"""AvaliadorAlertas: cor do semáforo de cada indicador (RF17) a partir da tabela parametro_alerta (RN08)."""
from acesso_dados import Repositorio
from servicos.erros import ErroValidacao

VERDE, AMARELO, VERMELHO = "verde", "amarelo", "vermelho"

NOMES_INDICADORES = {
    "atendimento_meta": "Atendimento da meta",
    "indice_defeitos": "Índice de defeitos",
    "indice_retrabalho": "Índice de retrabalho",
}


class AvaliadorAlertas:
    def __init__(self, repo=None):
        self.repo = repo or Repositorio()
        self._limites = None

    def limites(self):
        if self._limites is None:
            self._limites = {l["indicador"]: l for l in self.repo.consultar("SELECT * FROM parametro_alerta")}
        return self._limites

    def classificar(self, indicador, valor):
        """Verde, amarelo ou vermelho. None quando o indicador não tem limites ou não tem valor (ex.: sem meta)."""
        limite = self.limites().get(indicador)
        if limite is None or valor is None:
            return None
        verde, amarelo = limite["limite_verde"], limite["limite_amarelo"]
        if limite["sentido"] == "maior_melhor":
            return VERDE if valor >= verde else AMARELO if valor >= amarelo else VERMELHO
        return VERDE if valor <= verde else AMARELO if valor <= amarelo else VERMELHO

    def salvar_limites(self, indicador, limite_verde, limite_amarelo):
        """UC16: o Supervisor ajusta os limites sem mexer no código. Recusa limites incoerentes."""
        limite = self.limites().get(indicador)
        if limite is None:
            raise ErroValidacao("Indicador sem limites cadastrados.")
        if limite_verde is None or limite_amarelo is None or limite_verde < 0 or limite_amarelo < 0:
            raise ErroValidacao("Informe limites maiores ou iguais a zero.")
        nome = NOMES_INDICADORES.get(indicador, indicador)
        if limite["sentido"] == "maior_melhor" and limite_amarelo >= limite_verde:
            raise ErroValidacao(f"{nome}: maior é melhor, então o limite amarelo deve ser menor que o verde.")
        if limite["sentido"] == "menor_melhor" and limite_amarelo <= limite_verde:
            raise ErroValidacao(f"{nome}: menor é melhor, então o limite amarelo deve ser maior que o verde.")
        self.repo.executar("UPDATE parametro_alerta SET limite_verde = ?, limite_amarelo = ? WHERE indicador = ?",
                           (limite_verde, limite_amarelo, indicador))
        self._limites = None
