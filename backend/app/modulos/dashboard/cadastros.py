"""Metas, perdas, turnos, tipos de perda e limites do semáforo (portado de dashboard/servicos/registro.py,
importador_csv.py, cadastros.py e alertas.py).

Regras:
- RN09  Uma meta por dia, turno e modelo: gravar de novo a mesma combinação atualiza a quantidade.
- RN07  Perda exige tipo e quantidade maior que zero.
- RN06  Importação CSV é tudo ou nada: uma linha inválida recusa o arquivo, e a resposta diz linha, coluna e problema.
- RN08  Limites do semáforo coerentes com o sentido do indicador (maior é melhor: amarelo < verde; menor: amarelo > verde).
"""
import csv
import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tempo
from app.core.erros import ErroNegocio, NaoEncontrado
from app.modulos.dashboard.constantes import MAX_LINHAS_CSV, NOMES_INDICADORES, Indicador, Sentido
from app.modulos.dashboard.modelos import Limite, Meta, Perda, TipoPerda, Turno
from app.modulos.qualidade.modelos import Estacao
from app.modulos.rastreabilidade.modelos import Modelo
from app.modulos.usuarios.modelos import Usuario

# ---------------------------------------------------------------- consultas de apoio


def listar_turnos(sessao: Session) -> list[Turno]:
    return list(sessao.scalars(select(Turno).order_by(Turno.hora_inicio)))


def listar_tipos_perda(sessao: Session, incluir_inativos: bool = False) -> list[TipoPerda]:
    consulta = select(TipoPerda)
    if not incluir_inativos:
        consulta = consulta.where(TipoPerda.ativo.is_(True))
    return list(sessao.scalars(consulta.order_by(TipoPerda.nome)))


def _exigir(sessao: Session, modelo, item_id: int, nome: str):
    item = sessao.get(modelo, item_id)
    if item is None:
        raise ErroNegocio(f"{nome} não encontrado(a).", status=422)
    return item


# ---------------------------------------------------------------- metas


def gravar_meta(sessao: Session, executor: Usuario, *, data: date, turno_id: int, modelo_id: int, quantidade: int) -> Meta:
    """Cria ou atualiza a meta da combinação dia + turno + modelo (RN09)."""
    _exigir(sessao, Turno, turno_id, "Turno")
    _exigir(sessao, Modelo, modelo_id, "Modelo")
    if quantidade <= 0:
        raise ErroNegocio("A meta deve ser maior que zero.", status=422)
    meta = sessao.scalar(select(Meta).where(Meta.data == data, Meta.turno_id == turno_id, Meta.modelo_id == modelo_id))
    if meta is None:
        meta = Meta(data=data, turno_id=turno_id, modelo_id=modelo_id)
        sessao.add(meta)
    meta.quantidade = quantidade
    meta.registrado_por_id = executor.id
    meta.registrado_em = tempo.agora()
    sessao.flush()
    sessao.refresh(meta)
    return meta


def excluir_meta(sessao: Session, meta_id: int) -> None:
    meta = sessao.get(Meta, meta_id)
    if meta is None:
        raise NaoEncontrado("Meta não encontrada.")
    sessao.delete(meta)
    sessao.flush()


def listar_metas(sessao: Session, de: date, ate: date) -> list[Meta]:
    return list(sessao.scalars(select(Meta).where(Meta.data >= de, Meta.data <= ate)
                               .order_by(Meta.data.desc(), Meta.turno_id, Meta.modelo_id)))


# ---------------------------------------------------------------- perdas


def registrar_perda(sessao: Session, executor: Usuario, *, data: date, turno_id: int, estacao_id: int, modelo_id: int,
                    tipo_perda_id: int, quantidade: int, observacao: str | None = None, origem: str = "manual") -> Perda:
    _exigir(sessao, Turno, turno_id, "Turno")
    _exigir(sessao, Estacao, estacao_id, "Estação")
    _exigir(sessao, Modelo, modelo_id, "Modelo")
    tipo = _exigir(sessao, TipoPerda, tipo_perda_id, "Tipo de perda")
    if not tipo.ativo:
        raise ErroNegocio(f"O tipo de perda '{tipo.nome}' está inativo.", status=422)
    if quantidade <= 0:
        raise ErroNegocio("A quantidade perdida deve ser maior que zero (RN07).", status=422)
    if data > tempo.agora().astimezone(tempo.FUSO_FABRICA).date():
        raise ErroNegocio("A data da perda não pode estar no futuro.", status=422)
    perda = Perda(data=data, turno_id=turno_id, estacao_id=estacao_id, modelo_id=modelo_id, tipo_perda_id=tipo_perda_id,
                  quantidade=quantidade, observacao=(observacao or "").strip() or None, origem=origem,
                  registrado_por_id=executor.id, registrado_em=tempo.agora())
    sessao.add(perda)
    sessao.flush()
    sessao.refresh(perda)
    return perda


def excluir_perda(sessao: Session, perda_id: int) -> None:
    perda = sessao.get(Perda, perda_id)
    if perda is None:
        raise NaoEncontrado("Perda não encontrada.")
    sessao.delete(perda)
    sessao.flush()


# ---------------------------------------------------------------- importação CSV (tudo ou nada)


def _normalizar(texto: str | None) -> str:
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(sem_acento.lower().split())


@dataclass
class ErroLinha:
    linha: int
    coluna: str
    mensagem: str


@dataclass
class ResultadoImportacao:
    linhas_lidas: int = 0
    importadas: int = 0
    erros: list[ErroLinha] = field(default_factory=list)


COLUNAS_CSV = {
    "metas": ["data", "turno", "modelo", "quantidade"],
    "perdas": ["data", "turno", "estacao", "modelo", "tipo", "quantidade", "observacao"],
}


class _Leitor:
    """Lê as células de uma linha, guardando os erros com linha e coluna."""

    def __init__(self, sessao: Session):
        self.turnos = {_normalizar(t.nome): t.id for t in listar_turnos(sessao)}
        self.modelos = {}
        for m in sessao.scalars(select(Modelo)):
            self.modelos[_normalizar(m.nome)] = m.id
            self.modelos[_normalizar(m.codigo)] = m.id
        self.estacoes = {_normalizar(e.nome): e.id for e in sessao.scalars(select(Estacao).where(Estacao.ativo.is_(True)))}
        self.tipos = {_normalizar(t.nome): t.id for t in listar_tipos_perda(sessao)}
        self.erros: list[ErroLinha] = []

    def erro(self, linha: int, coluna: str, mensagem: str) -> None:
        self.erros.append(ErroLinha(linha, coluna, mensagem))

    def data(self, n: int, valor: str) -> date | None:
        texto = (valor or "").strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(texto, formato).date()
            except ValueError:
                pass
        self.erro(n, "data", f"'{texto}' não é uma data (use AAAA-MM-DD ou DD/MM/AAAA).")
        return None

    def inteiro(self, n: int, coluna: str, valor: str) -> int | None:
        try:
            numero = int((valor or "").strip())
        except ValueError:
            self.erro(n, coluna, f"'{valor}' não é um número inteiro.")
            return None
        if numero <= 0:
            self.erro(n, coluna, "Deve ser maior que zero.")
            return None
        return numero

    def nome(self, n: int, coluna: str, valor: str, tabela: dict[str, int], rotulo: str) -> int | None:
        item = tabela.get(_normalizar(valor))
        if item is None:
            self.erro(n, coluna, f"{rotulo} '{(valor or '').strip()}' não cadastrado(a).")
        return item


def _linhas_csv(conteudo: str, tipo: str) -> list[dict[str, str]]:
    texto = conteudo.lstrip("﻿")
    if not texto.strip():
        raise ErroNegocio("O arquivo está vazio.", status=422)
    primeira = texto.splitlines()[0]
    leitor = csv.DictReader(io.StringIO(texto), delimiter=";" if primeira.count(";") >= primeira.count(",") else ",")
    cabecalho = [_normalizar(c) for c in (leitor.fieldnames or [])]
    faltando = [c for c in COLUNAS_CSV[tipo] if c != "observacao" and c not in cabecalho]
    if faltando:
        raise ErroNegocio(f"Faltam as colunas: {', '.join(faltando)}. Use o modelo de planilha.", status=422)
    linhas = [{_normalizar(k): (v or "") for k, v in linha.items() if k} for linha in leitor]
    if len(linhas) > MAX_LINHAS_CSV:
        raise ErroNegocio(f"O arquivo passa de {MAX_LINHAS_CSV} linhas; divida em partes.", status=422)
    return linhas


def importar_csv(sessao: Session, executor: Usuario, tipo: str, conteudo: str) -> ResultadoImportacao:
    """Valida o arquivo inteiro antes de gravar qualquer linha (RN06). Linha 2 = primeira linha de dados."""
    if tipo not in COLUNAS_CSV:
        raise NaoEncontrado("Tipo de importação inexistente. Use: metas ou perdas.")
    linhas = _linhas_csv(conteudo, tipo)
    ler = _Leitor(sessao)
    hoje = tempo.agora().astimezone(tempo.FUSO_FABRICA).date()
    validas = []
    chaves_meta = set()
    for n, l in enumerate(linhas, start=2):
        antes = len(ler.erros)
        valores = {
            "data": ler.data(n, l.get("data")),
            "turno_id": ler.nome(n, "turno", l.get("turno"), ler.turnos, "Turno"),
            "modelo_id": ler.nome(n, "modelo", l.get("modelo"), ler.modelos, "Modelo"),
            "quantidade": ler.inteiro(n, "quantidade", l.get("quantidade")),
        }
        if tipo == "perdas":
            valores["estacao_id"] = ler.nome(n, "estacao", l.get("estacao"), ler.estacoes, "Estação")
            valores["tipo_perda_id"] = ler.nome(n, "tipo", l.get("tipo"), ler.tipos, "Tipo de perda")
            valores["observacao"] = l.get("observacao")
            if valores["data"] and valores["data"] > hoje:
                ler.erro(n, "data", "A data da perda não pode estar no futuro.")
        else:
            chave = (valores["data"], valores["turno_id"], valores["modelo_id"])
            if None not in chave and chave in chaves_meta:
                ler.erro(n, "data", "Meta repetida no arquivo para o mesmo dia, turno e modelo (RN09).")
            chaves_meta.add(chave)
        if len(ler.erros) == antes:
            validas.append(valores)
    resultado = ResultadoImportacao(linhas_lidas=len(linhas), erros=ler.erros)
    if ler.erros:
        return resultado
    for v in validas:
        if tipo == "metas":
            gravar_meta(sessao, executor, **v)
        else:
            registrar_perda(sessao, executor, origem="csv", **v)
    resultado.importadas = len(validas)
    return resultado


def modelo_csv(tipo: str) -> str:
    """Planilha modelo com o cabeçalho e uma linha de exemplo (abre no Excel em português)."""
    exemplos = {
        "metas": "2026-11-12;1º turno;AMT N14;120",
        "perdas": "2026-11-12;1º turno;Montagem Final;AMT N14;Componente danificado;3;Conector quebrado na montagem",
    }
    if tipo not in COLUNAS_CSV:
        raise NaoEncontrado("Tipo de importação inexistente. Use: metas ou perdas.")
    return "﻿" + ";".join(COLUNAS_CSV[tipo]) + "\r\n" + exemplos[tipo] + "\r\n"


# ---------------------------------------------------------------- turnos, tipos de perda e limites


def alterar_turno(sessao: Session, turno_id: int, *, nome: str, hora_inicio: time, hora_fim: time) -> Turno:
    turno = sessao.get(Turno, turno_id)
    if turno is None:
        raise NaoEncontrado("Turno não encontrado.")
    if hora_fim <= hora_inicio:
        raise ErroNegocio("O fim do turno deve ser depois do início.", status=422)
    for outro in listar_turnos(sessao):
        if outro.id != turno_id and hora_inicio < outro.hora_fim and outro.hora_inicio < hora_fim:
            raise ErroNegocio(f"O horário se sobrepõe ao {outro.nome}.", status=409)
        if outro.id != turno_id and _normalizar(outro.nome) == _normalizar(nome):
            raise ErroNegocio(f"Já existe o turno '{outro.nome}'.", status=409)
    turno.nome, turno.hora_inicio, turno.hora_fim = nome.strip(), hora_inicio, hora_fim
    sessao.flush()
    return turno


def criar_tipo_perda(sessao: Session, *, nome: str) -> TipoPerda:
    nome = nome.strip()
    if any(_normalizar(t.nome) == _normalizar(nome) for t in listar_tipos_perda(sessao, True)):
        raise ErroNegocio(f"Já existe o tipo de perda '{nome}'.", status=409)
    tipo = TipoPerda(nome=nome)
    sessao.add(tipo)
    sessao.flush()
    return tipo


def alterar_tipo_perda(sessao: Session, tipo_id: int, *, ativo: bool) -> TipoPerda:
    tipo = sessao.get(TipoPerda, tipo_id)
    if tipo is None:
        raise NaoEncontrado("Tipo de perda não encontrado.")
    tipo.ativo = ativo
    sessao.flush()
    return tipo


def salvar_limites(sessao: Session, indicador: Indicador, *, limite_verde: float, limite_amarelo: float) -> Limite:
    """UC16: o Supervisor ajusta os limites sem mexer no código. Recusa limites incoerentes."""
    limite = sessao.get(Limite, indicador.value)
    if limite is None:
        raise NaoEncontrado("Indicador sem limites cadastrados.")
    nome = NOMES_INDICADORES[indicador]
    if limite_verde < 0 or limite_amarelo < 0:
        raise ErroNegocio("Informe limites maiores ou iguais a zero.", status=422)
    if limite.sentido == Sentido.MAIOR_MELHOR and limite_amarelo >= limite_verde:
        raise ErroNegocio(f"{nome}: maior é melhor, então o limite amarelo deve ser menor que o verde.", status=422)
    if limite.sentido == Sentido.MENOR_MELHOR and limite_amarelo <= limite_verde:
        raise ErroNegocio(f"{nome}: menor é melhor, então o limite amarelo deve ser maior que o verde.", status=422)
    limite.limite_verde, limite.limite_amarelo = limite_verde, limite_amarelo
    sessao.flush()
    return limite
