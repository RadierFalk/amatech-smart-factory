"""Camada 3 — Acesso a dados.

A classe Repositorio é a única parte do sistema que executa SQL. As outras camadas pedem dados a ela.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import config

_bancos_prontos = set()   # caminhos já conferidos nesta execução (evita reabrir o script a cada consulta)


class Repositorio:
    def __init__(self, caminho=None):
        self.caminho = Path(caminho or config.CAMINHO_BANCO)
        self._conexao_transacao = None
        self._garantir_banco()

    # ------------------------------------------------------------ conexão
    def _conectar(self):
        conexao = sqlite3.connect(self.caminho, timeout=15)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")   # sem isso o SQLite ignora as chaves estrangeiras (RNF04)
        return conexao

    def _garantir_banco(self):
        """Cria o banco a partir do script SQL na primeira execução (arquivo inexistente ou vazio)."""
        chave = str(self.caminho.resolve())
        if chave in _bancos_prontos:
            return
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        conexao = self._conectar()
        try:
            existe = conexao.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'usuario'").fetchone()
            if not existe:
                conexao.executescript(config.SCRIPT_BANCO.read_text(encoding="utf-8"))
                conexao.commit()
        finally:
            conexao.close()
        _bancos_prontos.add(chave)

    # ------------------------------------------------------------ operações
    def consultar(self, sql, params=()):
        """Executa um SELECT e devolve uma lista de dicionários."""
        if self._conexao_transacao is not None:
            return [dict(l) for l in self._conexao_transacao.execute(sql, params).fetchall()]
        conexao = self._conectar()
        try:
            return [dict(l) for l in conexao.execute(sql, params).fetchall()]
        finally:
            conexao.close()

    def consultar_um(self, sql, params=()):
        linhas = self.consultar(sql, params)
        return linhas[0] if linhas else None

    def executar(self, sql, params=()):
        """Executa INSERT, UPDATE ou DELETE. Fora de uma transação, grava na hora. Devolve o id inserido."""
        if self._conexao_transacao is not None:
            return self._conexao_transacao.execute(sql, params).lastrowid
        conexao = self._conectar()
        try:
            cursor = conexao.execute(sql, params)
            conexao.commit()
            return cursor.lastrowid
        finally:
            conexao.close()

    @contextmanager
    def transacao(self):
        """Agrupa várias gravações: ou todas são gravadas, ou nenhuma (usada na importação, RN06)."""
        if self._conexao_transacao is not None:   # transação já aberta: participa dela
            yield self
            return
        conexao = self._conectar()
        self._conexao_transacao = conexao
        try:
            yield self
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            self._conexao_transacao = None
            conexao.close()
