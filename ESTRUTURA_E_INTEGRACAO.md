# Rastreabilidade de Produtos: estrutura e integração (OA3)

**Setor:** Rastreabilidade e fluxo de materiais · **Projeto 2 → Problema 5** · Pasta no repositório único: `rastreabilidade/`

Este documento resume como o sistema está organizado hoje, o que foi alterado para a integração da OA3 e como ele
conversa com os outros três sistemas da AMATECH Smart Factory. O resumo de todos os setores está em
[`../RESUMO_ALTERACOES.md`](../RESUMO_ALTERACOES.md).

## 1. O sistema

| Item | Valor |
| --- | --- |
| Tecnologia | Python + FastAPI + SQLite (`sqlite3` puro); telas em HTML/CSS/JS servidas pela própria API |
| Porta | **8000** (API e telas) |
| Banco | `database/amatech.db`, criado na primeira execução com dados de demonstração (fora do Git) |
| Dono dos cadastros | **Modelos de notebook** (AMT N14 a N18) e **números de série** (`AMT-000001`...) |
| Executar | `python -m uvicorn app.main:app --port 8000` → http://localhost:8000 |
| Testes | `python -m pytest -q` (37 testes) |

## 2. Estrutura atual

```
rastreabilidade/
├── app/
│   ├── main.py              ← cria a API FastAPI, registra as rotas e serve as telas (static/)
│   ├── config.py            ← caminho do banco, fuso, chaves de API (inclui as chaves de demonstração da OA3)
│   ├── db.py                ← conexão SQLite; inicializar() aplica migrações, povoa e cria as chaves de demonstração
│   ├── migracoes.py         ← aplica database/migracoes/*.sql sem apagar tabelas existentes
│   ├── seed.py              ← dados de demonstração (30 produções com histórico)
│   ├── schemas.py           ← modelos de entrada (Pydantic)
│   ├── seguranca.py         ← login por token e permissões por cargo
│   ├── erros.py             ← ErroNegocio (respostas {"detail": ...})
│   ├── routers/             ← rotas HTTP: auth, cadastros, producao, materiais, relatorios, maquinas, integracao
│   └── servicos/            ← regras de negócio: cadastros, producao, materiais, relatorios, integracao
├── database/migracoes/      ← 001_base.sql, 002_integracao.sql
├── static/                  ← telas (index.html, css/, js/)
├── tests/                   ← test_api.py (inclui TestEcossistema) e test_servicos.py
├── tools/verificar_conflitos.py
└── docs/INTEGRACAO.md       ← contrato completo da API /api/v1
```

## 3. O que foi alterado na OA3

| Alteração | Arquivos |
| --- | --- |
| Nova rota **`GET /api/v1/passagens?de=&ate=&status=&limite=`**: histórico de etapas de todas as produções no período (datas ISO 8601 em UTC). Diferente da fila `/eventos`, inclui o histórico de demonstração | `app/routers/integracao.py`, `app/servicos/integracao.py` |
| **`POST /api/v1/producoes/{serie}/status`** aceita `descricao_falha`, `motivo_reprovacao` e `id_externo` (opcionais). Ao reprovar, a não conformidade usa a falha real e grava `origem_sistema` e `id_externo`; um reenvio com o mesmo `id_externo` não reprova de novo | `app/schemas.py`, `app/servicos/producao.py`, `app/servicos/integracao.py` |
| **Chaves de demonstração** `qualidade`, `dashboard` e `manutencao`, criadas ao iniciar só se o nome ainda não existir | `app/config.py`, `app/db.py`, `app/servicos/integracao.py` |
| Testes novos (`TestEcossistema`). O `TestIntegracao` desliga as chaves de demonstração, porque cria as próprias | `tests/test_api.py` |
| Documentação das rotas novas e das variáveis | `docs/INTEGRACAO.md` |

Sem os campos novos, a API se comporta exatamente como antes (a rota de máquinas/IoT continua igual).

## 4. Comunicação com os outros sistemas

```
Qualidade (5000) ──POST /api/v1/producoes/{serie}/status──►  Rastreabilidade (8000)
Qualidade (5000) ──GET  /api/v1/producoes─────────────────►  (busca os números de série)
Dashboard (8501) ──GET  /api/v1/produtos, /api/v1/passagens►  (modelos e produção)
```

| Quem chama | Rota | Para quê | Chave (`X-API-Key`) |
| --- | --- | --- | --- |
| Qualidade | `GET /api/v1/producoes?limite=1000` | Cadastrar os notebooks (série e modelo) na Qualidade | `amt_demo_qualidade` |
| Qualidade | `GET /api/v1/producoes/{serie}` | Ver a etapa atual antes de aprovar | `amt_demo_qualidade` |
| Qualidade | `POST /api/v1/producoes/{serie}/status` | Ocorrência **Reprovado** → etapa Reprovado (com a falha real e `id_externo = QLD-<id>`); **Em_reprocesso** → Reprovado e depois Em Montagem; **Aprovado** → Aprovado | `amt_demo_qualidade` |
| Dashboard | `GET /api/v1/produtos` | Cadastrar os modelos no Dashboard | `amt_demo_dashboard` |
| Dashboard | `GET /api/v1/passagens?de=&ate=` | Contar Aprovados e Reprovados por dia, turno e modelo (produção do painel) | `amt_demo_dashboard` |

O sistema **não chama** nenhum outro: só responde. Todas as datas saem em UTC com "Z"; quem consome converte para o
horário de Manaus (UTC-4).

## 5. Variáveis de ambiente

| Variável | Para quê | Padrão |
| --- | --- | --- |
| `AMATECH_DB` | Caminho do banco | `database/amatech.db` |
| `AMATECH_API_KEY` | Chave da rota de máquinas/IoT | `amatech-iot-demo` |
| `AMATECH_CHAVES_DEMO` | `0` desliga a criação das chaves de demonstração | `1` |
| `AMATECH_CHAVE_QUALIDADE`, `AMATECH_CHAVE_DASHBOARD`, `AMATECH_CHAVE_MANUTENCAO` | Chaves de demonstração | `amt_demo_qualidade`, `amt_demo_dashboard`, `amt_demo_manutencao` |

## 6. Como conferir

```bash
python -m pytest -q
curl -H "X-API-Key: amt_demo_dashboard" "http://localhost:8000/api/v1/passagens?status=Aprovado"
curl -X POST -H "X-API-Key: amt_demo_qualidade" -H "Content-Type: application/json" \
     -d '{"status":"Reprovado","descricao_falha":"Tela sem imagem","motivo_reprovacao":"Tela (Maior)","id_externo":"QLD-1"}' \
     http://localhost:8000/api/v1/producoes/AMT-000017/status
```
