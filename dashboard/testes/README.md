# testes/ — Testes

Testes das fórmulas e das regras de negócio. Cada requisito da matriz de rastreabilidade (`docs/relatorio_oa2.md`, seção 10) deve ter pelo menos um teste.

Casos de referência (dados do enunciado), com resultado esperado:

| Teste | Entrada | Esperado |
| --- | --- | --- |
| Atendimento da meta | produção 1.420, meta 1.500 | 94,7% (amarelo) |
| Índice de defeitos | 60 reprovados em 1.420 | 4,2% (amarelo) |
| Produtividade | 1.420 em turno de 480 min com 85 min de parada | 215,7 unid/h |
| Integridade | aprovados + reprovados ≠ realizada | registro recusado |
| Meta duplicada | mesma data, turno e produto | registro recusado (RN09) |
| Importação com erro | planilha com 1 linha inválida | nada gravado (RN06) |

Ferramenta de testes: **pytest**. Cada teste usa um banco novo numa pasta temporária, criado pelo script SQL (`conftest.py`), então os testes nunca mexem no `database/banco.db`.

```bash
python -m pytest testes -q
```

| Arquivo | O que testa |
| --- | --- |
| `test_indicadores.py` | As fórmulas com os casos de referência acima, o semáforo e os limites (RN08), o período do filtro (RN05) e a parada em andamento |
| `test_registro.py` | Integridade dos registros, meta duplicada (RN09), retrabalho sem motivo (RN02), paradas, atualização de registros externos, sinônimos dos cadastros comuns, login e permissões |
| `test_conector.py` | Sincronização com os outros setores (APIs simuladas): conversão de UTC, contagem da produção, defeitos e retrabalho, paradas, atualização sem duplicar, RN06 por setor e sistema fora do ar |
| `test_importador.py` | Importação tudo ou nada (RN06), erros por linha e coluna, coluna ausente, separador e codificação, modelos CSV e sincronização sem duplicar |
