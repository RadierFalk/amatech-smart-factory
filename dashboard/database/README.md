# database/ — Camada 4: Dados

| Arquivo | Conteúdo |
| --- | --- |
| `banco_dashboard_industrial.sql` | Script de criação: 17 tabelas, restrições, índices e dados de teste (versão final da OA2) |
| `banco.db` | Banco gerado pelo script; **não vai para o Git** (está no `.gitignore`) |
| `modelos_csv/` | (a criar na S3) modelos de planilha para a tela de Importação |

Para criar o banco:

```bash
python -c "import sqlite3; sqlite3.connect('database/banco.db').executescript(open('database/banco_dashboard_industrial.sql', encoding='utf-8').read())"
```

Os indicadores **não** ficam no banco: são calculados pela CalculadoraIndicadores (`servicos/`). Os dados de teste usam os números do exemplo do enunciado (meta 1.500, produção 1.420, 60 reprovados, parada de 85 min). Há um usuário de teste por perfil (lista no README principal), apenas para testes. Os modelos de planilha CSV ficam em `modelos_csv/`.
