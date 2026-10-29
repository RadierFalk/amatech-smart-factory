"""ImportadorCSV: lê, valida e grava planilhas CSV (RF16), tudo ou nada (RN06).

Cada linha passa pelo ServicoRegistro, com as mesmas regras dos formulários. Os nomes escritos na planilha
(turno, produto, estação, tipo...) são traduzidos para os ids do banco pelo ServicoCadastros, que também
aceita os sinônimos dos cadastros comuns do ecossistema.

A sincronização com os outros setores (ConectorEcossistema) entra pelo mesmo caminho: monta as linhas no
formato da planilha, com origem_sistema e id_externo, e chama importar_linhas.
"""
import csv
import io
from dataclasses import dataclass, field

import pandas as pd

import config
from acesso_dados import Repositorio
from modelos import Importacao
from servicos.cadastros import CADASTROS
from servicos.cadastros_comuns import normalizar
from servicos.erros import ErroValidacao
from servicos.formatos import ler_data, texto_data_hora
from servicos.registro import ServicoRegistro

# Colunas de cada tipo de planilha (contexto, seção 7.3). As opcionais podem faltar no arquivo ou ficar vazias.
# Retrabalho não tem planilha própria: vai nas colunas opcionais do defeito que o gerou.
MODELOS = {
    "producao": {
        "titulo": "Produção",
        "colunas": ["data", "turno", "produto", "qtd_realizada", "qtd_aprovada", "qtd_reprovada"],
        "opcionais": [],
        "exemplo": ["16/08/2026", "1º turno", "Notebook modelo A", "1450", "1400", "50"],
    },
    "defeito": {
        "titulo": "Defeitos e retrabalho",
        "colunas": ["data", "turno", "produto", "tipo_defeito", "estacao", "maquina_codigo", "quantidade",
                    "data_hora", "observacao", "estacao_retorno", "motivo_retrabalho", "qtd_retrabalho"],
        "opcionais": ["maquina_codigo", "observacao", "estacao_retorno", "motivo_retrabalho", "qtd_retrabalho"],
        "exemplo": ["16/08/2026", "1º turno", "Notebook modelo A", "Falha no teclado", "Teste funcional", "TST-02",
                    "12", "16/08/2026 09:40", "Teclas travando", "Montagem final", "Troca do teclado", "12"],
    },
    "parada": {
        "titulo": "Paradas",
        "colunas": ["estacao", "maquina_codigo", "turno", "motivo", "inicio", "fim", "observacao"],
        "opcionais": ["maquina_codigo", "fim", "observacao"],
        "exemplo": ["Teste funcional", "TST-02", "1º turno", "Falha de equipamento", "16/08/2026 10:00",
                    "16/08/2026 10:45", "Cabo de teste rompido"],
    },
    "perda": {
        "titulo": "Perdas",
        "colunas": ["data", "turno", "estacao", "produto", "tipo_perda", "quantidade", "observacao"],
        "opcionais": ["observacao"],
        "exemplo": ["16/08/2026", "1º turno", "Linha SMT", "Notebook modelo A", "Componente danificado", "8", ""],
    },
}
COLUNAS_RETRABALHO = ("estacao_retorno", "motivo_retrabalho", "qtd_retrabalho")


@dataclass
class ResultadoImportacao:
    status: str                      # concluida, rejeitada ou valida (validar_arquivo: nada foi gravado)
    lidas: int = 0
    importadas: int = 0
    rejeitadas: int = 0
    erros: list = field(default_factory=list)   # (linha, coluna, problema)
    id_importacao: int | None = None

    @property
    def aceita(self):
        return self.status != "rejeitada"


class _Desfazer(Exception):
    """Interrompe a transação da importação para desfazer tudo o que já foi gravado (RN06)."""


def _valor(linha, coluna):
    """Valor de uma coluna, ou None se ela não existir ou estiver vazia."""
    valor = linha.get(coluna)
    if valor is None or valor != valor:   # None ou NaN
        return None
    if isinstance(valor, str):
        return valor.strip() or None
    return valor


def _nome_coluna(coluna):
    """'Data Hora' -> 'data_hora'; 'Estação' -> 'estacao'."""
    return normalizar(coluna).replace(" ", "_")


class ImportadorCSV:
    def __init__(self, repo=None):
        self.repo = repo or Repositorio()
        self.registro = ServicoRegistro(self.repo)
        self.cadastros = self.registro.cadastros

    # ------------------------------------------------------------ modelos para download (T07, passo 2)
    @staticmethod
    def modelo_csv(tipo):
        """Arquivo modelo com o cabeçalho e uma linha de exemplo, em UTF-8 com BOM e ';' (abre certo no Excel)."""
        modelo = MODELOS[tipo]
        saida = io.StringIO()
        escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
        escritor.writerow(modelo["colunas"])
        escritor.writerow(modelo["exemplo"])
        return saida.getvalue().encode("utf-8-sig")

    @classmethod
    def gerar_modelos(cls, pasta=None):
        pasta = pasta or config.PASTA_MODELOS_CSV
        pasta.mkdir(parents=True, exist_ok=True)
        for tipo in MODELOS:
            (pasta / f"modelo_{tipo}.csv").write_bytes(cls.modelo_csv(tipo))

    # ------------------------------------------------------------ leitura
    @staticmethod
    def ler_arquivo(conteudo):
        """Lê o CSV como texto. Aceita ';' ou ',' e UTF-8 (com ou sem BOM) ou o padrão do Excel em português."""
        try:
            texto = conteudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = conteudo.decode("cp1252", errors="replace")
        if not texto.strip():
            raise ErroValidacao("O arquivo está vazio.")
        cabecalho = texto.lstrip().splitlines()[0]
        separador = ";" if cabecalho.count(";") >= cabecalho.count(",") else ","
        try:
            tabela = pd.read_csv(io.StringIO(texto), sep=separador, dtype=str, keep_default_na=False,
                                 skip_blank_lines=False)
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as erro:
            raise ErroValidacao(f"Não foi possível ler o arquivo como CSV: {erro}") from erro
        tabela.columns = [_nome_coluna(c) for c in tabela.columns]
        return tabela

    # ------------------------------------------------------------ importação (UC10)
    def importar(self, conteudo, tipo, usuario_id, nome_arquivo):
        return self._importar_arquivo(conteudo, tipo, usuario_id, nome_arquivo, simular=False)

    def validar_arquivo(self, conteudo, tipo, usuario_id, nome_arquivo=""):
        """Faz a importação inteira e desfaz no fim: mostra os erros antes de gravar (T07, prévia)."""
        return self._importar_arquivo(conteudo, tipo, usuario_id, nome_arquivo, simular=True)

    def _importar_arquivo(self, conteudo, tipo, usuario_id, nome_arquivo, simular):
        try:
            tabela = self.ler_arquivo(conteudo)
        except ErroValidacao as erro:
            erros = [(1, None, mensagem) for _, mensagem in erro.problemas]
            return self._rejeitar(tipo, usuario_id, nome_arquivo, 0, erros, simular)
        return self.importar_linhas(tabela.to_dict("records"), tipo, usuario_id, nome_arquivo, simular=simular,
                                    colunas=list(tabela.columns))

    def importar_linhas(self, linhas, tipo, usuario_id, nome_arquivo, numero_inicial=2, simular=False, colunas=None):
        """Valida e grava as linhas numa transação só. Qualquer erro desfaz tudo (RN06).

        `linhas` são dicionários com as colunas de MODELOS[tipo]; podem trazer também origem_sistema e
        id_externo (sincronização). `numero_inicial` é o número da primeira linha no arquivo (a 1 é o cabeçalho).
        """
        if tipo not in MODELOS:
            raise ErroValidacao(("tipo", f"Tipo de dado desconhecido: {tipo}."))
        modelo = MODELOS[tipo]
        numeradas = [(numero_inicial + i, linha) for i, linha in enumerate(linhas)
                     if any(_valor(linha, c) is not None for c in linha)]   # ignora linhas em branco
        if colunas is None:
            colunas = set().union(*(linha.keys() for _, linha in numeradas))
        faltando = [c for c in modelo["colunas"] if c not in modelo["opcionais"] and c not in colunas]
        if faltando:
            erros = [(1, c, "Coluna obrigatória ausente no cabeçalho.") for c in faltando]
            return self._rejeitar(tipo, usuario_id, nome_arquivo, len(numeradas), erros, simular,
                                  rejeitadas=len(numeradas))
        if not numeradas:
            return self._rejeitar(tipo, usuario_id, nome_arquivo, 0, [(1, None, "O arquivo não tem linhas de dados.")],
                                  simular)

        gravar_linha = getattr(self, f"_linha_{tipo}")
        erros = []
        id_importacao = None
        try:
            with self.repo.transacao():
                id_importacao = self._registrar(Importacao(nome_arquivo=nome_arquivo, tipo_dado=tipo,
                                                           linhas_lidas=len(numeradas),
                                                           linhas_importadas=len(numeradas)), usuario_id)
                for numero, linha in numeradas:
                    erros.extend((numero, coluna, problema)
                                 for coluna, problema in gravar_linha(linha, usuario_id, id_importacao))
                if erros or simular:
                    raise _Desfazer
        except _Desfazer:
            pass
        if erros:
            return self._rejeitar(tipo, usuario_id, nome_arquivo, len(numeradas), erros, simular)
        if simular:
            return ResultadoImportacao("valida", len(numeradas), len(numeradas), 0)
        return ResultadoImportacao("concluida", len(numeradas), len(numeradas), 0, id_importacao=id_importacao)

    # ------------------------------------------------------------ registro da importação (tabela importacao)
    def _registrar(self, importacao, usuario_id):
        return self.repo.executar(
            "INSERT INTO importacao (nome_arquivo, tipo_dado, data_hora, id_usuario, linhas_lidas, linhas_importadas, "
            "linhas_rejeitadas, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (importacao.nome_arquivo or "(sem nome)", importacao.tipo_dado, texto_data_hora(config.agora()),
             usuario_id, importacao.linhas_lidas, importacao.linhas_importadas, importacao.linhas_rejeitadas,
             importacao.situacao))

    def _rejeitar(self, tipo, usuario_id, nome_arquivo, lidas, erros, simular, rejeitadas=None):
        """A tentativa recusada também fica no histórico (fora da transação, que já foi desfeita)."""
        if rejeitadas is None:
            rejeitadas = len({linha for linha, _, _ in erros if linha > 1})
        resultado = ResultadoImportacao("rejeitada", lidas, 0, rejeitadas, erros)
        if not simular and tipo in MODELOS:
            resultado.id_importacao = self._registrar(Importacao(nome_arquivo=nome_arquivo, tipo_dado=tipo,
                                                                 linhas_lidas=lidas, linhas_rejeitadas=rejeitadas,
                                                                 situacao="rejeitada"), usuario_id)
        return resultado

    # ------------------------------------------------------------ tradução de nomes e chamadas ao ServicoRegistro
    def _procurar(self, cadastro, linha, coluna, problemas, obrigatorio=True):
        """Id do cadastro escrito na coluna (ex.: '1º turno' -> 1). Anota o problema se não encontrar."""
        valor = _valor(linha, coluna)
        if valor is None:
            if obrigatorio:
                problemas.append((coluna, "Campo obrigatório vazio."))
            return None
        id_registro = self.cadastros.buscar_id(cadastro, valor)
        if id_registro is None:
            problemas.append((coluna, f"\"{valor}\" não está cadastrado em {CADASTROS[cadastro]['titulo']}."))
        return id_registro

    @staticmethod
    def _chamar(problemas, funcao, *args, **kwargs):
        """Chama o ServicoRegistro e junta os problemas dele aos da tradução, sem repetir uma coluna já apontada."""
        try:
            return funcao(*args, **kwargs)
        except ErroValidacao as erro:
            apontadas = {coluna for coluna, _ in problemas}
            problemas.extend((coluna, mensagem) for coluna, mensagem in erro.problemas if coluna not in apontadas)
            return None

    @staticmethod
    def _externo(linha):
        return {"origem_sistema": _valor(linha, "origem_sistema"), "id_externo": _valor(linha, "id_externo")}

    # ------------------------------------------------------------ uma linha de cada tipo
    def _linha_producao(self, linha, usuario_id, id_importacao):
        problemas = []
        id_turno = self._procurar("turno", linha, "turno", problemas)
        id_produto = self._procurar("produto", linha, "produto", problemas)
        self._chamar(problemas, self.registro.registrar_producao, _valor(linha, "data"), id_turno, id_produto,
                     _valor(linha, "qtd_realizada"), _valor(linha, "qtd_aprovada"), _valor(linha, "qtd_reprovada"),
                     usuario_id, id_importacao=id_importacao, **self._externo(linha))
        return problemas

    def _linha_defeito(self, linha, usuario_id, id_importacao):
        problemas = []
        data = ler_data(_valor(linha, "data"))
        if data is None:
            problemas.append(("data", "Data inválida: use AAAA-MM-DD ou DD/MM/AAAA."))
        id_turno = self._procurar("turno", linha, "turno", problemas)
        id_produto = self._procurar("produto", linha, "produto", problemas)
        id_tipo = self._procurar("tipo_defeito", linha, "tipo_defeito", problemas)
        id_estacao = self._procurar("estacao", linha, "estacao", problemas)
        id_maquina = self._procurar("maquina", linha, "maquina_codigo", problemas, obrigatorio=False)
        id_producao = None
        if data and id_turno and id_produto:   # todo defeito pertence a um registro de produção (decisão 5.2.4)
            id_producao = self.registro.buscar_producao(data, id_turno, id_produto)
            if id_producao is None:
                problemas.append(("data", f"Não há produção registrada em {data:%d/%m/%Y}, {_valor(linha, 'turno')}, "
                                          f"{_valor(linha, 'produto')}. Importe a produção antes dos defeitos."))
        externo = self._externo(linha)
        id_defeito = self._chamar(problemas, self.registro.registrar_defeito, id_producao, id_tipo, id_estacao,
                                  _valor(linha, "quantidade"), _valor(linha, "data_hora"), usuario_id,
                                  id_maquina=id_maquina, observacao=_valor(linha, "observacao"),
                                  id_importacao=id_importacao, **externo)

        if any(_valor(linha, c) is not None for c in COLUNAS_RETRABALHO):   # o defeito gerou retrabalho (RN02)
            id_retorno = self._procurar("estacao", linha, "estacao_retorno", problemas)
            if id_defeito:
                self._chamar(problemas, self.registro.registrar_retrabalho, id_defeito, id_retorno,
                             _valor(linha, "motivo_retrabalho"), _valor(linha, "qtd_retrabalho"),
                             _valor(linha, "data_hora"), usuario_id, **externo)
        return problemas

    def _linha_parada(self, linha, usuario_id, id_importacao):
        problemas = []
        id_estacao = self._procurar("estacao", linha, "estacao", problemas)
        id_maquina = self._procurar("maquina", linha, "maquina_codigo", problemas, obrigatorio=False)
        id_turno = self._procurar("turno", linha, "turno", problemas)
        id_motivo = self._procurar("motivo_parada", linha, "motivo", problemas)
        self._chamar(problemas, self.registro.registrar_parada, id_estacao, id_turno, id_motivo,
                     _valor(linha, "inicio"), usuario_id, fim=_valor(linha, "fim"), id_maquina=id_maquina,
                     observacao=_valor(linha, "observacao"), id_importacao=id_importacao, **self._externo(linha))
        return problemas

    def _linha_perda(self, linha, usuario_id, id_importacao):
        problemas = []
        id_turno = self._procurar("turno", linha, "turno", problemas)
        id_estacao = self._procurar("estacao", linha, "estacao", problemas)
        id_produto = self._procurar("produto", linha, "produto", problemas)
        id_tipo = self._procurar("tipo_perda", linha, "tipo_perda", problemas)
        self._chamar(problemas, self.registro.registrar_perda, _valor(linha, "data"), id_turno, id_estacao,
                     id_produto, id_tipo, _valor(linha, "quantidade"), usuario_id,
                     observacao=_valor(linha, "observacao"), id_importacao=id_importacao)
        return problemas
