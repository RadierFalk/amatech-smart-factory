"""ServicoCadastros: listas básicas (turnos, produtos, estações, máquinas e tipos), usadas pelos formulários,
pela importação e pela tela de Cadastros (T09, UC03).

Também traduz nomes vindos de planilhas e de outros sistemas para os ids do banco (buscar_id), usando
os cadastros comuns do ecossistema (servicos/cadastros_comuns.py).
"""
import re
import sqlite3

from acesso_dados import Repositorio
from servicos.cadastros_comuns import SINONIMOS, normalizar
from servicos.erros import ErroValidacao

# Como cada lista é guardada no banco e editada na tela de Cadastros
CADASTROS = {
    "turno": {"titulo": "Turnos", "tabela": "turno", "chave": "id_turno", "nome": "nome",
              "colunas": ["nome", "hora_inicio", "hora_fim", "duracao_min"],
              "obrigatorias": ["nome", "hora_inicio", "hora_fim", "duracao_min"]},
    "produto": {"titulo": "Produtos", "tabela": "produto", "chave": "id_produto", "nome": "modelo",
                "colunas": ["modelo", "descricao", "ativo"], "obrigatorias": ["modelo"]},
    "estacao": {"titulo": "Estações", "tabela": "estacao", "chave": "id_estacao", "nome": "nome",
                "colunas": ["nome", "setor", "ordem_fluxo"], "obrigatorias": ["nome"]},
    "maquina": {"titulo": "Máquinas", "tabela": "maquina", "chave": "id_maquina", "nome": "codigo",
                "colunas": ["codigo", "nome", "id_estacao"], "obrigatorias": ["codigo", "nome", "id_estacao"]},
    "tipo_defeito": {"titulo": "Tipos de defeito", "tabela": "tipo_defeito", "chave": "id_tipo_defeito",
                     "nome": "descricao", "colunas": ["descricao", "categoria"], "obrigatorias": ["descricao"]},
    "motivo_parada": {"titulo": "Motivos de parada", "tabela": "motivo_parada", "chave": "id_motivo",
                      "nome": "descricao", "colunas": ["descricao", "tipo"], "obrigatorias": ["descricao", "tipo"]},
    "tipo_perda": {"titulo": "Tipos de perda", "tabela": "tipo_perda", "chave": "id_tipo_perda",
                   "nome": "descricao", "colunas": ["descricao"], "obrigatorias": ["descricao"]},
}
TIPOS_MOTIVO = ("corretiva", "preventiva", "operacional")
CATEGORIAS_DEFEITO = ("funcional", "visual", "documental")
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _minutos(hora):
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


class ServicoCadastros:
    def __init__(self, repo=None):
        self.repo = repo or Repositorio()

    # ------------------------------------------------------------ consultas
    def listar(self, cadastro):
        c = CADASTROS[cadastro]
        return self.repo.consultar(f"SELECT * FROM {c['tabela']} ORDER BY {c['chave']}")

    def listar_turnos(self):
        return self.listar("turno")

    def listar_produtos(self, apenas_ativos=True):
        filtro = "WHERE ativo = 1" if apenas_ativos else ""
        return self.repo.consultar(f"SELECT * FROM produto {filtro} ORDER BY modelo")

    def listar_estacoes(self):
        return self.repo.consultar("SELECT * FROM estacao ORDER BY ordem_fluxo, nome")

    def listar_maquinas(self, id_estacao=None):
        sql = """SELECT m.*, e.nome AS estacao FROM maquina m JOIN estacao e ON e.id_estacao = m.id_estacao"""
        if id_estacao:
            return self.repo.consultar(sql + " WHERE m.id_estacao = ? ORDER BY m.codigo", (id_estacao,))
        return self.repo.consultar(sql + " ORDER BY m.codigo")

    def listar_tipos_defeito(self):
        return self.repo.consultar("SELECT * FROM tipo_defeito ORDER BY descricao")

    def listar_motivos_parada(self):
        return self.repo.consultar("SELECT * FROM motivo_parada ORDER BY descricao")

    def listar_tipos_perda(self):
        return self.repo.consultar("SELECT * FROM tipo_perda ORDER BY descricao")

    def obter(self, cadastro, id_registro):
        c = CADASTROS[cadastro]
        return self.repo.consultar_um(f"SELECT * FROM {c['tabela']} WHERE {c['chave']} = ?", (id_registro,))

    def buscar_id(self, cadastro, texto):
        """Procura pelo nome (sem diferenciar maiúsculas e acentos) e pelos sinônimos dos cadastros comuns."""
        c = CADASTROS[cadastro]
        procurado = normalizar(texto)
        if not procurado:
            return None
        procurado = normalizar(SINONIMOS.get(cadastro, {}).get(procurado, procurado))
        for linha in self.repo.consultar(f"SELECT {c['chave']} AS id, {c['nome']} AS nome FROM {c['tabela']}"):
            if normalizar(linha["nome"]) == procurado:
                return linha["id"]
        return None

    def turno_por_horario(self, momento):
        """Turno em que um horário cai (ex.: 09:30 -> 1º turno). None se estiver fora de todos os turnos."""
        minuto = momento.hour * 60 + momento.minute
        for turno in self.listar_turnos():
            inicio, fim = _minutos(turno["hora_inicio"]), _minutos(turno["hora_fim"])
            dentro = inicio <= minuto < fim if inicio < fim else (minuto >= inicio or minuto < fim)
            if dentro:
                return turno
        return None

    # ------------------------------------------------------------ cadastros vindos do setor dono (sincronização)
    def garantir_produto(self, modelo, descricao=None):
        """Modelos de notebook vêm da Rastreabilidade: cria o produto aqui se ainda não existir."""
        id_produto = self.buscar_id("produto", modelo)
        if id_produto:
            return id_produto, False
        return self.repo.executar("INSERT INTO produto (modelo, descricao) VALUES (?, ?)",
                                  (modelo.strip(), descricao)), True

    def garantir_maquina(self, codigo, nome, id_estacao):
        """Máquinas vêm da Manutenção: cria a máquina aqui se ainda não existir (a tag é a chave comum)."""
        id_maquina = self.buscar_id("maquina", codigo)
        if id_maquina:
            return id_maquina, False
        return self.repo.executar("INSERT INTO maquina (codigo, nome, id_estacao) VALUES (?, ?, ?)",
                                  (codigo.strip().upper(), nome.strip(), id_estacao)), True

    # ------------------------------------------------------------ edição pela tela de Cadastros (T09)
    def salvar(self, cadastro, linhas):
        """Grava as linhas editadas de uma lista. Linhas sem id são novas. Tudo ou nada."""
        c = CADASTROS[cadastro]
        problemas = []
        preparadas = []
        for numero, linha in enumerate(linhas, start=1):
            valores = {col: self._limpar(linha.get(col)) for col in c["colunas"]}
            if cadastro == "produto" and valores["ativo"] is None:   # produto novo entra ativo
                valores["ativo"] = 1
            for col in c["obrigatorias"]:
                if valores[col] in (None, ""):
                    problemas.append((col, f"Linha {numero}: preencha '{col}'."))
            problemas += [(col, f"Linha {numero}: {msg}") for col, msg in self._validar(cadastro, valores)]
            preparadas.append((linha.get(c["chave"]), valores))
        if problemas:
            raise ErroValidacao(problemas)
        try:
            with self.repo.transacao():
                for chave, valores in preparadas:
                    colunas = list(valores)
                    if chave in (None, "") or chave != chave:   # chave != chave: NaN vindo da tabela editável
                        self.repo.executar(
                            f"INSERT INTO {c['tabela']} ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
                            [valores[col] for col in colunas])
                    else:
                        self.repo.executar(
                            f"UPDATE {c['tabela']} SET {', '.join(col + ' = ?' for col in colunas)} WHERE {c['chave']} = ?",
                            [valores[col] for col in colunas] + [int(chave)])
        except sqlite3.IntegrityError as erro:
            if "UNIQUE" in str(erro):
                raise ErroValidacao("Já existe um item com esse nome ou código.") from erro
            raise ErroValidacao("Os dados violam uma regra do banco: " + str(erro)) from erro
        return len(preparadas)

    @staticmethod
    def _limpar(valor):
        if valor is None or valor != valor:   # None ou NaN
            return None
        if isinstance(valor, str):
            valor = valor.strip()
            return valor or None
        if isinstance(valor, bool):
            return int(valor)
        if isinstance(valor, float) and valor.is_integer():
            return int(valor)
        return valor

    def _validar(self, cadastro, v):
        if cadastro == "turno":
            for col in ("hora_inicio", "hora_fim"):
                if v[col] and not _HORA.match(str(v[col])):
                    yield col, f"'{col}' deve estar no formato HH:MM."
            if v["duracao_min"] is not None and (not str(v["duracao_min"]).isdigit() or int(v["duracao_min"]) <= 0):
                yield "duracao_min", "a duração do turno deve ser um número de minutos maior que zero."
        elif cadastro == "motivo_parada" and v["tipo"] and v["tipo"] not in TIPOS_MOTIVO:
            yield "tipo", "o tipo deve ser corretiva, preventiva ou operacional."
        elif cadastro == "tipo_defeito" and v["categoria"] and v["categoria"] not in CATEGORIAS_DEFEITO:
            yield "categoria", "a categoria deve ser funcional, visual ou documental."
        elif cadastro == "maquina" and v["id_estacao"] and not self.obter("estacao", v["id_estacao"]):
            yield "id_estacao", "estação inexistente."
