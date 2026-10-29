"""ServicoRegistro: valida (RN01 a RN09) e grava os eventos da linha (RF01 a RF05, RF15).

Os formulários, a importação de planilhas e a sincronização com os outros setores passam todos por aqui,
então um dado só entra no banco depois de passar pelas mesmas regras.

Dados vindos de outro sistema trazem origem_sistema e id_externo. Se esse par já existe no banco, o registro
é atualizado em vez de duplicado (ex.: um chamado de manutenção que estava aberto e agora foi concluído).
"""
from acesso_dados import Repositorio
from modelos import (Defeito, Estacao, MetaProducao, Parada, Perda, Produto, RegistroProducao, Retrabalho,
                     Turno)
from servicos.cadastros import ServicoCadastros
from servicos.erros import ErroValidacao
from servicos.formatos import ler_data, ler_data_hora, texto_data, texto_data_hora


def _inteiro(valor, campo, rotulo, problemas, minimo=0):
    try:
        numero = float(str(valor).strip().replace(",", ".")) if not isinstance(valor, (int, float)) else valor
        if numero != int(numero):
            raise ValueError
        numero = int(numero)
    except (TypeError, ValueError):
        problemas.append((campo, f"{rotulo} deve ser um número inteiro."))
        return None
    if numero < minimo:
        problemas.append((campo, f"{rotulo} deve ser maior {'que zero' if minimo == 1 else 'ou igual a zero'}."))
        return None
    return numero


def _texto(valor):
    texto = str(valor).strip() if valor is not None and valor == valor else ""
    return texto or None


class ServicoRegistro:
    def __init__(self, repo=None):
        self.repo = repo or Repositorio()
        self.cadastros = ServicoCadastros(self.repo)

    # ------------------------------------------------------------ apoio
    def _exigir(self, cadastro, id_registro, campo, rotulo, problemas, obrigatorio=True):
        if id_registro in (None, ""):
            if obrigatorio:
                problemas.append((campo, f"Informe {rotulo}."))
            return None
        linha = self.cadastros.obter(cadastro, id_registro)
        if linha is None:
            problemas.append((campo, f"{rotulo[0].upper() + rotulo[1:]} não está cadastrado(a)."))
        return linha

    def _data(self, valor, campo, problemas):
        data = ler_data(valor)
        if data is None:
            problemas.append((campo, "Data inválida: use AAAA-MM-DD ou DD/MM/AAAA."))
        return data

    def _data_hora(self, valor, campo, problemas, obrigatorio=True):
        if valor in (None, "") or valor != valor:
            if obrigatorio:
                problemas.append((campo, "Informe a data e a hora."))
            return None
        momento = ler_data_hora(valor)
        if momento is None:
            problemas.append((campo, "Data e hora inválidas: use AAAA-MM-DD HH:MM ou DD/MM/AAAA HH:MM."))
        return momento

    def _existente(self, tabela, chave, origem_sistema, id_externo):
        if not id_externo:
            return None
        linha = self.repo.consultar_um(f"SELECT {chave} AS id FROM {tabela} WHERE origem_sistema = ? AND id_externo = ?",
                                       (origem_sistema, id_externo))
        return linha["id"] if linha else None

    def _gravar(self, tabela, chave, valores, origem_sistema=None, id_externo=None):
        """INSERT, ou UPDATE quando o registro externo (origem_sistema, id_externo) já existe."""
        if id_externo:
            valores = dict(valores, origem_sistema=origem_sistema, id_externo=id_externo)
        existente = self._existente(tabela, chave, origem_sistema, id_externo)
        colunas = list(valores)
        if existente:
            self.repo.executar(f"UPDATE {tabela} SET {', '.join(c + ' = ?' for c in colunas)} WHERE {chave} = ?",
                               [valores[c] for c in colunas] + [existente])
            return existente
        return self.repo.executar(f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({', '.join('?' * len(colunas))})",
                                  [valores[c] for c in colunas])

    # ------------------------------------------------------------ metas (RF02, RN09)
    def registrar_meta(self, data, id_turno, id_produto, qtd_meta, registrado_por):
        problemas = []
        data = self._data(data, "data", problemas)
        turno = self._exigir("turno", id_turno, "turno", "o turno", problemas)
        produto = self._exigir("produto", id_produto, "produto", "o produto", problemas)
        qtd = _inteiro(qtd_meta, "qtd_meta", "A meta", problemas, minimo=1)
        if not problemas and self.repo.consultar_um(
                "SELECT 1 AS ok FROM meta_producao WHERE data = ? AND id_turno = ? AND id_produto = ?",
                (texto_data(data), id_turno, id_produto)):
            problemas.append(("data", f"Já existe meta para {data:%d/%m/%Y}, {turno['nome']}, {produto['modelo']} (RN09)."))
        if problemas:
            raise ErroValidacao(problemas)
        meta = MetaProducao(data=data, turno=Turno(**{k: turno[k] for k in ("nome", "hora_inicio", "hora_fim", "duracao_min")}),
                            produto=Produto(modelo=produto["modelo"]), qtd_meta=qtd)
        return self.repo.executar(
            "INSERT INTO meta_producao (data, id_turno, id_produto, qtd_meta, registrado_por) VALUES (?, ?, ?, ?, ?)",
            (texto_data(meta.data), id_turno, id_produto, meta.qtd_meta, registrado_por))

    # ------------------------------------------------------------ produção (RF01, RN01, RNF04)
    def registrar_producao(self, data, id_turno, id_produto, qtd_realizada, qtd_aprovada, qtd_reprovada,
                           registrado_por, id_importacao=None, origem_sistema=None, id_externo=None):
        problemas = []
        data = self._data(data, "data", problemas)                                   # RN01
        turno = self._exigir("turno", id_turno, "turno", "o turno", problemas)        # RN01
        produto = self._exigir("produto", id_produto, "produto", "o produto", problemas)  # RN01
        realizada = _inteiro(qtd_realizada, "qtd_realizada", "A quantidade realizada", problemas)
        aprovada = _inteiro(qtd_aprovada, "qtd_aprovada", "A quantidade aprovada", problemas)
        reprovada = _inteiro(qtd_reprovada, "qtd_reprovada", "A quantidade reprovada", problemas)
        if None not in (realizada, aprovada, reprovada) and aprovada + reprovada != realizada:
            problemas.append(("qtd_reprovada", "Aprovados + reprovados diferente do realizado (RNF04)."))
        if problemas:
            raise ErroValidacao(problemas)
        registro = RegistroProducao(data=data, turno=Turno(nome=turno["nome"], hora_inicio=turno["hora_inicio"],
                                                           hora_fim=turno["hora_fim"], duracao_min=turno["duracao_min"]),
                                    produto=Produto(modelo=produto["modelo"]), qtd_realizada=realizada,
                                    qtd_aprovada=aprovada, qtd_reprovada=reprovada)
        return self._gravar("registro_producao", "id_producao", {
            "data": texto_data(registro.data), "id_turno": id_turno, "id_produto": id_produto,
            "qtd_realizada": registro.qtd_realizada, "qtd_aprovada": registro.qtd_aprovada,
            "qtd_reprovada": registro.qtd_reprovada, "registrado_por": registrado_por, "id_importacao": id_importacao,
        }, origem_sistema, id_externo)

    def buscar_producao(self, data, id_turno, id_produto):
        """Registro de produção de uma data, turno e produto (todo defeito pertence a um, decisão 5.2.4)."""
        linha = self.repo.consultar_um(
            "SELECT id_producao FROM registro_producao WHERE data = ? AND id_turno = ? AND id_produto = ? "
            "ORDER BY id_producao LIMIT 1", (texto_data(data), id_turno, id_produto))
        return linha["id_producao"] if linha else None

    # ------------------------------------------------------------ defeitos (RF03)
    def registrar_defeito(self, id_producao, id_tipo_defeito, id_estacao, quantidade, data_hora, registrado_por,
                          id_maquina=None, observacao=None, id_importacao=None, origem_sistema=None, id_externo=None):
        problemas = []
        if not id_producao or not self.repo.consultar_um(
                "SELECT 1 AS ok FROM registro_producao WHERE id_producao = ?", (id_producao,)):
            problemas.append(("data", "Escolha o registro de produção de origem do defeito."))
        tipo = self._exigir("tipo_defeito", id_tipo_defeito, "tipo_defeito", "o tipo de defeito", problemas)
        estacao = self._exigir("estacao", id_estacao, "estacao", "a estação", problemas)
        maquina = self._exigir("maquina", id_maquina, "maquina_codigo", "a máquina", problemas, obrigatorio=False)
        qtd = _inteiro(quantidade, "quantidade", "A quantidade", problemas, minimo=1)
        momento = self._data_hora(data_hora, "data_hora", problemas)
        if problemas:
            raise ErroValidacao(problemas)
        defeito = Defeito(tipo=tipo["descricao"], estacao=Estacao(nome=estacao["nome"]), quantidade=qtd,
                          data_hora=momento, observacao=_texto(observacao))
        return self._gravar("defeito", "id_defeito", {
            "id_producao": id_producao, "id_tipo_defeito": id_tipo_defeito, "id_estacao": id_estacao,
            "id_maquina": maquina["id_maquina"] if maquina else None, "quantidade": defeito.quantidade,
            "data_hora": texto_data_hora(defeito.data_hora), "observacao": defeito.observacao,
            "registrado_por": registrado_por, "id_importacao": id_importacao,
        }, origem_sistema, id_externo)

    # ------------------------------------------------------------ retrabalho (RF04, RN02)
    def registrar_retrabalho(self, id_defeito, id_estacao_retorno, motivo, quantidade, data_hora, registrado_por,
                             origem_sistema=None, id_externo=None):
        problemas = []
        if not id_defeito or not self.repo.consultar_um("SELECT 1 AS ok FROM defeito WHERE id_defeito = ?", (id_defeito,)):
            problemas.append(("defeito", "Escolha o defeito que gerou o retrabalho."))
        estacao = self._exigir("estacao", id_estacao_retorno, "estacao_retorno", "a estação de retorno", problemas)  # RN02
        motivo = _texto(motivo)
        if not motivo:
            problemas.append(("motivo_retrabalho", "Informe o motivo do retrabalho (RN02)."))                         # RN02
        qtd = _inteiro(quantidade, "qtd_retrabalho", "A quantidade em retrabalho", problemas, minimo=1)
        momento = self._data_hora(data_hora, "data_hora", problemas)
        if problemas:
            raise ErroValidacao(problemas)
        retrabalho = Retrabalho(estacao_retorno=Estacao(nome=estacao["nome"]), motivo=motivo, quantidade=qtd,
                                data_hora=momento)
        return self._gravar("retrabalho", "id_retrabalho", {
            "id_defeito": id_defeito, "id_estacao_retorno": id_estacao_retorno, "motivo": retrabalho.motivo,
            "quantidade": retrabalho.quantidade, "data_hora": texto_data_hora(retrabalho.data_hora),
            "registrado_por": registrado_por,
        }, origem_sistema, id_externo)

    # ------------------------------------------------------------ paradas (RF05, RN04)
    def registrar_parada(self, id_estacao, id_turno, id_motivo, inicio, registrado_por, fim=None, id_maquina=None,
                         observacao=None, id_importacao=None, origem_sistema=None, id_externo=None):
        problemas = []
        estacao = self._exigir("estacao", id_estacao, "estacao", "a estação", problemas)
        turno = self._exigir("turno", id_turno, "turno", "o turno", problemas)
        motivo = self._exigir("motivo_parada", id_motivo, "motivo", "o motivo da parada", problemas)   # RN04
        maquina = self._exigir("maquina", id_maquina, "maquina_codigo", "a máquina", problemas, obrigatorio=False)
        inicio = self._data_hora(inicio, "inicio", problemas)
        fim = self._data_hora(fim, "fim", problemas, obrigatorio=False)
        if inicio and fim and fim <= inicio:
            problemas.append(("fim", "O fim da parada deve ser depois do início (RNF04)."))
        if problemas:
            raise ErroValidacao(problemas)
        parada = Parada(estacao=Estacao(nome=estacao["nome"]), turno=Turno(nome=turno["nome"], hora_inicio=turno["hora_inicio"],
                        hora_fim=turno["hora_fim"], duracao_min=turno["duracao_min"]), motivo=motivo["descricao"],
                        inicio=inicio, fim=fim, observacao=_texto(observacao))
        return self._gravar("parada", "id_parada", {
            "id_estacao": id_estacao, "id_maquina": maquina["id_maquina"] if maquina else None, "id_turno": id_turno,
            "id_motivo": id_motivo, "inicio": texto_data_hora(parada.inicio),
            "fim": texto_data_hora(parada.fim) if parada.fim else None, "observacao": parada.observacao,
            "registrado_por": registrado_por, "id_importacao": id_importacao,
        }, origem_sistema, id_externo)

    def encerrar_parada(self, id_parada, fim):
        """A máquina voltou: grava o fim. A duração é calculada, nunca digitada (decisão 5.2.5)."""
        linha = self.repo.consultar_um("SELECT inicio, fim FROM parada WHERE id_parada = ?", (id_parada,))
        if linha is None:
            raise ErroValidacao("Parada não encontrada.")
        if linha["fim"]:
            raise ErroValidacao("Esta parada já foi encerrada.")
        problemas = []
        fim = self._data_hora(fim, "fim", problemas)
        if fim and fim <= ler_data_hora(linha["inicio"]):
            problemas.append(("fim", "O fim da parada deve ser depois do início (RNF04)."))
        if problemas:
            raise ErroValidacao(problemas)
        self.repo.executar("UPDATE parada SET fim = ? WHERE id_parada = ?", (texto_data_hora(fim), id_parada))

    # ------------------------------------------------------------ perdas (RF15, RN07)
    def registrar_perda(self, data, id_turno, id_estacao, id_produto, id_tipo_perda, quantidade, registrado_por,
                        observacao=None, id_importacao=None):
        problemas = []
        data = self._data(data, "data", problemas)
        self._exigir("turno", id_turno, "turno", "o turno", problemas)
        estacao = self._exigir("estacao", id_estacao, "estacao", "a estação", problemas)
        produto = self._exigir("produto", id_produto, "produto", "o produto", problemas)
        tipo = self._exigir("tipo_perda", id_tipo_perda, "tipo_perda", "o tipo de perda", problemas)       # RN07
        qtd = _inteiro(quantidade, "quantidade", "A quantidade perdida", problemas, minimo=1)             # RN07
        if problemas:
            raise ErroValidacao(problemas)
        perda = Perda(data=data, tipo=tipo["descricao"], quantidade=qtd, estacao=Estacao(nome=estacao["nome"]),
                      produto=Produto(modelo=produto["modelo"]))
        return self.repo.executar(
            "INSERT INTO perda (data, id_turno, id_estacao, id_produto, id_tipo_perda, quantidade, observacao, "
            "registrado_por, id_importacao) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (texto_data(perda.data), id_turno, id_estacao, id_produto, id_tipo_perda, perda.quantidade,
             _texto(observacao), registrado_por, id_importacao))
