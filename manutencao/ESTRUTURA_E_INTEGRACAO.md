# Controle da Manutenção: estrutura e integração (OA3)

**Setor:** Manutenção · **Projeto 5 → Problema 4** · Pasta no repositório único: `manutencao/`

Este documento resume como o sistema está organizado hoje, o que foi alterado para a integração da OA3 e como ele
conversa com os outros três sistemas da AMATECH Smart Factory. O resumo de todos os setores está em
[`../RESUMO_ALTERACOES.md`](../RESUMO_ALTERACOES.md). A especificação original do projeto continua em `docs/01` a `docs/05`.

## 1. O sistema

| Item | Valor |
| --- | --- |
| Tecnologia | Python + Streamlit (telas) + FastAPI (API) + SQLite |
| Portas | Telas **8503** · API **5002** (sobe junto com as telas, numa thread) |
| Banco | `manutencao.db` (está no Git); criado a partir de `docs/02_DATABASE_SCHEMA.sql` se não existir |
| Dono dos cadastros | **Máquinas** (TAGs como `TEST-01`) e chamados de manutenção |
| Executar | `streamlit run app.py` → http://localhost:8503 · só a API: `python api.py` |
| Testes | `python -m pytest -q` (10 testes) |

## 2. Estrutura atual

```
manutencao/
├── app.py                   ← entrada do Streamlit: login, menu por perfil; sobe a API em segundo plano
├── api.py                   ← API FastAPI (porta 5002): status, equipamentos, chamados (GET e POST), indicadores
├── config.py                ← caminhos, portas, chave da API de integração, cores e listas do sistema
├── database.py              ← conexão SQLite, criação do banco e migração da integração
├── init_db.py
├── models/                  ← entidades e schemas
├── services/
│   ├── auth_service.py      ← login e permissões por perfil
│   ├── chamado_service.py   ← ciclo de vida da OS (abrir, assumir, laudo, peças, concluir); abertura externa
│   ├── equipamento_service.py ← máquinas e peças
│   └── relatorio_service.py ← downtime, MTTR, MTTA e disponibilidade
├── pages/                   ← 01_painel_maquinas … 07_cadastros
├── ui_components.py         ← estilos e componentes visuais
├── docs/                    ← especificação (01–05), schema SQL e 06_INTEGRACAO_ECOSSISTEMA.md
├── tests/                   ← test_management_control.py e test_integracao_ecossistema.py (novo)
├── manutencao.db
└── .streamlit/config.toml   ← tema e, agora, porta 8503
```

## 3. O que foi alterado na OA3

| Alteração | Arquivos |
| --- | --- |
| Nova rota **`POST /api/manutencao/chamados`** (cabeçalho `X-API-Key`): outro sistema abre um chamado pela TAG da máquina. Usa o mesmo `abrir_chamado` da tela, então valem as mesmas regras | `api.py`, `services/chamado_service.py` (`abrir_chamado_externo`) |
| **Usuário de serviço** "Integração (outros sistemas)" (`SVC-INTEGRACAO`, OPERADOR, **inativo**, não faz login), operador de abertura desses chamados | `database.py`, `docs/02_DATABASE_SCHEMA.sql` |
| **Migração automática e idempotente** ao iniciar, também em bancos antigos e sem apagar nada: colunas `origem_sistema` e `id_externo` em `chamados_manutencao` (índice único), máquinas **INS-01** e **QC-01** (usadas pela Qualidade) e o usuário de serviço | `database.py`, `docs/02_DATABASE_SCHEMA.sql`, `manutencao.db` |
| `GET /api/manutencao/chamados`: datas com **"Z"** (o banco sempre gravou em UTC) e campos `origem_sistema` e `id_externo` | `api.py`, `services/chamado_service.py` |
| `MANUTENCAO_DB` (caminho do banco) e `MANUTENCAO_API_KEY` (chave do POST) | `config.py` |
| Tela fixada na porta 8503, sem mudar o tema | `.streamlit/config.toml` |
| Testes novos e seção 4 da documentação de integração | `tests/test_integracao_ecossistema.py`, `docs/06_INTEGRACAO_ECOSSISTEMA.md` |

## 4. Comunicação com os outros sistemas

```
Qualidade (5000) ──GET  /api/equipamentos────────► Manutenção (5002)   (TAGs das máquinas)
Qualidade (5000) ──POST /api/manutencao/chamados─►                     (defeito causado pela máquina)
Dashboard (8501) ──GET  /api/equipamentos────────►                     (máquinas e estação de cada uma)
Dashboard (8501) ──GET  /api/manutencao/chamados─►                     (paradas)
```

**`POST /api/manutencao/chamados`** (chave `amatech-manutencao-demo`):

```json
{"equipamento_tag": "TEST-01", "descricao_falha": "Teclado: teclas sem resposta (ocorrência QLD-12 da Qualidade)",
 "prioridade": "ALTA", "tipo_manutencao": "CORRETIVA", "origem_sistema": "qualidade", "id_externo": "QLD-12"}
```

| Resposta | Quando |
| --- | --- |
| `201 {"id_chamado": 4, "criado": true}` | Chamado aberto; a máquina passa para **PARADA** |
| `200 {"id_chamado": 4, "criado": false}` | Reenvio com o mesmo `origem_sistema` + `id_externo`: não duplica |
| `401` / `404` / `409` / `422` | Chave inválida / TAG não existe / máquina já parada ou em manutenção (RN02) / dados inválidos |

**Como o Dashboard usa os chamados:** cada chamado vira uma parada da máquina, da abertura ao fim do atendimento
(convertidos de UTC para Manaus). CORRETIVA = "Falha de equipamento"; PREVENTIVA = "Manutenção programada".
Chamados cancelados não contam, e um chamado sem fim aparece no painel como **parada em andamento**. O setor da máquina
define a estação no Dashboard ("Testes Funcionais" = "Teste funcional"; ver `docs/CADASTROS_COMUNS.md` do Dashboard).

As rotas `GET` continuam sem chave, como antes. O sistema **não chama** nenhum outro: só responde.

## 5. Variáveis de ambiente

| Variável | Para quê | Padrão |
| --- | --- | --- |
| `MANUTENCAO_API_KEY` | Chave do `POST /api/manutencao/chamados` | `amatech-manutencao-demo` |
| `MANUTENCAO_DB` | Caminho do banco | `manutencao.db` |
| `MANUTENCAO_API_PORT` | Porta da API | `5002` |

## 6. Como conferir

```bash
python -m pytest -q
curl -X POST -H "X-API-Key: amatech-manutencao-demo" -H "Content-Type: application/json" \
     -d '{"equipamento_tag":"EMB-01","descricao_falha":"Teste de integração","origem_sistema":"teste","id_externo":"T-1"}' \
     http://localhost:5002/api/manutencao/chamados
```

Na tela, o chamado aparece na fila com o operador "Integração (outros sistemas)", e a EMB-01 fica *PARADA*.
