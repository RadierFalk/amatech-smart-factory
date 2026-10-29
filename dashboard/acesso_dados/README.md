# acesso_dados/ — Camada 3: Acesso a dados

Contém `repositorio.py`, com a classe **Repositorio**: a única parte do sistema que escreve SQL.

- Métodos previstos: `consultar(sql, params)`, `executar(sql, params)` e `transacao()`.
- Sempre usar consultas parametrizadas (nunca montar SQL juntando textos).
- Ativar `PRAGMA foreign_keys = ON` em toda conexão, para o SQLite validar as chaves estrangeiras.
- A importação de CSV roda dentro de uma transação: uma linha inválida desfaz tudo (RN06).
