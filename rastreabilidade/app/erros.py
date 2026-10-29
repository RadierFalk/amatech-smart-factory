"""Erro de regra de negócio: vira uma resposta JSON {"detail": mensagem} com o status informado."""


class ErroNegocio(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
