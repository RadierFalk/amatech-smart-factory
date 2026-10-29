"""Erro de validação usado por todas as classes de serviço."""


class ErroValidacao(Exception):
    """Um ou mais problemas encontrados ao validar um dado.

    `problemas` é uma lista de (campo, mensagem). O campo permite à importação de CSV dizer em que coluna
    está o erro (RN06); nos formulários, só a mensagem é exibida.
    """

    def __init__(self, problemas):
        if isinstance(problemas, str):
            problemas = [(None, problemas)]
        self.problemas = list(problemas)
        super().__init__("; ".join(mensagem for _, mensagem in self.problemas))
