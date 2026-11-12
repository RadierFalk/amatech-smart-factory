"""Erros de negócio levantados pelos serviços e convertidos em respostas HTTP em app.main."""


class ErroNegocio(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


class NaoEncontrado(ErroNegocio):
    def __init__(self, mensagem: str = "Registro não encontrado."):
        super().__init__(mensagem, status=404)
