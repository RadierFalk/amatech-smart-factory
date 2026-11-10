# Passagem de tarefa: PostgreSQL no Docker + migração dos dados

> **Para:** um agente (Claude Code ou similar) numa máquina **com Docker**.
> **Branch:** `feature/angular`. Nunca trabalhe na `main`: ela continua rodando o sistema Streamlit atual.
> **Origem:** escrito em 2026-11-10 numa máquina sem Docker nem WSL. Lá, os testes que dependem de banco foram **pulados**, e não executados.

Antes de começar, rode `git log --oneline feature/angular` e leia a seção [Registro](#registro). O trabalho pode ter avançado depois que este arquivo foi escrito: módulos novos no `backend/`, migrações a mais etc.

---

## 1. Contexto em 1 minuto

O repositório é o ERP de uma fábrica de notebooks (AMATECH). Hoje são 4 sistemas de equipes diferentes, `rastreabilidade/`, `qualidade/`, `manutencao/` e `dashboard/`, unidos por um portal Streamlit (`portal/`). Cada um tem seu próprio SQLite. O `README.md` da raiz descreve o sistema atual.

**Decisões já tomadas pelo dono do projeto (não reabra essas discussões):**

| Tema | Decisão |
|---|---|
| Frontend | Sai o Streamlit, entra o **Angular**, numa **reescrita completa** (o Streamlit só é desligado no final) |
| Backend | **Uma API FastAPI única** em `backend/`, com um módulo por setor |
| Banco | **PostgreSQL**: um banco `amatech`, **um schema por módulo**: `usr`, `ras`, `qld`, `mnt`, `dsh` |
| Acesso a dados | SQLAlchemy 2.0 (ORM) + Alembic + psycopg 3 |
| Usuários | **Uma tabela só: `usr.usuarios`.** Todas as FKs de usuário dos módulos apontam para ela |
| Dados existentes | **Migrar os dados atuais** (não recriar com seeds) |
| Ambiente local | PostgreSQL **em contêiner, via Docker Compose** |

## 2. O que já existe em `backend/`

```
backend/
  app/main.py                    FastAPI: /api/saude, /api/docs, handler de ErroNegocio
  app/core/config.py             variáveis AMATECH_* (pydantic-settings, lê backend/.env)
  app/core/db.py                 engine, Base com convenção de nomes, SCHEMAS_MODULOS, obter_sessao
  app/core/seguranca.py          Argon2 (mesmos parâmetros do portal antigo) + JWT (PyJWT)
  app/core/rbac.py               6 personas (enum Perfil) + catálogo dos 5 módulos
  app/core/deps.py               usuario_atual, exigir_modulo(Modulo.X), exigir_perfis(...)
  app/modelos.py                 importa TODOS os modelos (usado pelo Alembic e pelos testes)
  app/modulos/usuarios/          modelo, esquemas, serviço e rotas de /api/auth e /api/usuarios
  alembic/versions/0001_usr_usuarios.py   cria os 5 schemas + usr.usuarios (escrita à mão)
  scripts/seed_demo.py           6 personas demo, só se usr.usuarios estiver vazia
  tests/test_core.py             16 testes sem banco (passando)
  tests/test_usuarios_api.py     11 testes de API (PULADOS sem Postgres: nunca rodaram)
docker-compose.dev.yml           postgres:17-alpine, bancos amatech e amatech_testes
.github/workflows/backend-testes.yml     CI: alembic upgrade + alembic check + pytest no Postgres
```

Rotas: `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/auth/modulos`, `GET|POST /api/usuarios`, `PATCH /api/usuarios/{id}`, `POST /api/usuarios/{id}/senha`.

**O que já foi validado sem Postgres:** testes de unidade, um teste de fumaça de todas as rotas com SQLite em memória e `alembic upgrade head --sql`, que gera DDL correto. **O que nunca rodou:** qualquer coisa contra um PostgreSQL de verdade.

---

## 3. Tarefa A: subir o Postgres e validar a fundação

Todos os comandos partem da raiz do repositório. No Windows, use `.venv\Scripts\python.exe` no lugar de `python`.

```bash
git checkout feature/angular && git pull

docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps          # espere STATUS "healthy"

python -m venv .venv && . .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

cd backend
cp .env.exemplo .env                                  # os valores padrão batem com o docker-compose.dev.yml
alembic upgrade head
alembic check                                         # esperado: "No new upgrade operations detected."
python -m pytest -q -rs                               # esperado: 27 passed, 0 skipped
python -m scripts.seed_demo
uvicorn app.main:app --port 8000
```

**Critérios de aceite (todos obrigatórios):**

- [ ] `alembic upgrade head` roda num banco vazio, e `alembic downgrade base` seguido de `alembic upgrade head` funciona.
- [ ] `alembic check` não acusa diferença entre os modelos e a migração. Se acusar, corrija a migração escrita à mão para bater com o modelo, e não o contrário, a menos que o modelo esteja errado.
- [ ] `pytest`: **0 skipped**. Um teste pulado significa que o banco não foi alcançado, e isso não conta como passar.
- [ ] `GET http://localhost:8000/api/saude` responde `{"api": "ok", "banco": "ok"}`.
- [ ] `POST /api/auth/login` com `{"matricula": "ADM-0001", "senha": "amatech1234"}` devolve um token, e `GET /api/auth/modulos` com esse token lista as 5 siglas.
- [ ] Os acentos aparecem corretos no banco: `SELECT perfil FROM usr.usuarios` mostra "Operador de Produção", e não "Produ��o".
- [ ] **Ponta a ponta com o Angular:** com a API no ar (porta 8000), rode `cd frontend && npm ci && npx ng serve` e abra http://localhost:4200. Entre como ADM-0001: o hub mostra 5 módulos, e em "Gestão de usuários" dá para criar um usuário, trocar a persona dele, desativá-lo e redefinir a senha. Recarregue a página e confira se os dados continuam lá (é isso que prova que estão gravados no Postgres). Entre como TEC-2001: só aparecem MNT e DSH, e abrir http://localhost:4200/usuarios leva de volta ao hub.

Se algo falhar, **corrija no código** e explique a causa no Registro. Não desative nem pule testes para fazer passar.

---

## 4. Tarefa B: script de migração dos dados (`backend/scripts/migrar_sqlite.py`)

### 4.1 De onde vêm os dados

| Origem | Arquivo | No Git? | Observação |
|---|---|---|---|
| Manutenção | `manutencao/manutencao.db` | **sim** | 6 tabelas, 11 usuários |
| Qualidade | `qualidade/banco/controle_qualidade.db` | **sim** | 6 tabelas, 6 usuários, 39 ocorrências |
| Rastreabilidade | `rastreabilidade/database/amatech.db` | não (gerado) | criado por `app/db.py` + `app/seed.py` na primeira execução |
| Dashboard | `dashboard/database/banco.db` | não (gerado) | criado a partir de `database/banco_dashboard_industrial.sql` |
| Portal | `portal/banco/erp_usuarios.db` | não (gerado) | criado por `portal/banco.py` (6 personas) |

Ignore `qualidade/banco/backups/`. Os dados de produção podem estar nos volumes do servidor Swarm (`dados-*` no `docker-compose.yml`). **Pergunte ao dono do projeto** se a migração deve usar esses volumes ou os arquivos do repositório. Até ter resposta, use os do repositório.

O script recebe os caminhos por argumento, com os acima como padrão. Se um arquivo não existir, o script avisa e segue para o próximo, sem falhar.

### 4.2 Escopo agora: só `usr.usuarios`

Os modelos de `ras`, `qld`, `mnt` e `dsh` **ainda não existem** no `backend/`, a não ser que o Registro diga o contrário. Por isso, implemente agora só a parte de usuários e deixe o script organizado em uma função por schema (`migrar_usr`, `migrar_mnt`...), para cada módulo ser acrescentado quando o modelo dele existir. O script **devolve o mapa `(origem, id_antigo) -> usr.usuarios.id`**, porque as FKs dos outros módulos vão precisar dele.

### 4.3 Regras para unificar usuários (conflitos reais encontrados)

A chave de unificação é a **matrícula** (em maiúsculas, sem espaços). Estado atual dos bancos versionados:

| Matrícula | Portal (fonte da verdade) | MNT | QLD | Senha gravada |
|---|---|---|---|---|
| ADM-0001 | Administrador | **GESTOR** | Administrador | MNT: texto puro `amatech123` · QLD: argon2 |
| GES-0001 | Supervisor / Gestor | GESTOR | **Administrador** | MNT: `123456` · QLD: argon2 |
| OPE-0001 | Operador de Produção | OPERADOR | Operador | MNT: `amatech123` · QLD: argon2 |
| QUA-0001 | Inspetor de Qualidade | **OPERADOR** | Inspetor de Qualidade | MNT: `amatech123` · QLD: argon2 |
| ALM-0001 | Almoxarife | **OPERADOR** | Almoxarife | MNT: `amatech123` · QLD: argon2 |
| TEC-2001 | Técnico de Manutenção | TECNICO | **Operador** | MNT: `123456` · QLD: argon2 |
| OP-10234, OP-10235 | — | OPERADOR | — | `123456` |
| TEC-2002 | — | TECNICO | — | `123456` |
| GES-0002 | — | GESTOR | — | `123456` |
| SVC-INTEGRACAO | — | OPERADOR, **inativo** | — | `!` (não faz login) |

Regras:

1. **Perfil:** use o do portal quando a matrícula estiver na lista das 6 personas (`scripts/seed_demo.py:PERSONAS`). Para quem só existe nos módulos, mapeie assim: MNT `OPERADOR`→Operador de Produção, `TECNICO`→Técnico de Manutenção, `GESTOR`→Supervisor / Gestor. Para a QLD, siga a mesma lógica pelo texto do perfil. Todo conflito resolvido entra no relatório.
2. **Nome:** o do portal. Se a matrícula não estiver no portal, use o primeiro nome não vazio na ordem MNT → QLD → RAS → DSH.
3. **Senha (nunca grave texto puro):**
   - as 6 personas recebem `gerar_hash("amatech1234")`, que é a senha documentada no README;
   - para os outros, um hash `$argon2` que já exista é mantido como está, porque os parâmetros são os mesmos;
   - um texto puro (`123456`, `amatech123`) vira `gerar_hash(texto)`, para o usuário continuar entrando com a mesma senha;
   - `!` (ou qualquer valor inválido) é mantido como está: a conta fica sem login possível, o que é o comportamento desejado para o `SVC-INTEGRACAO`.
4. **Ativo:** inativo se estiver inativo em **qualquer** origem.
5. **`criado_em`:** a menor data entre as origens, convertida de texto para `timestamptz` e tratada como UTC, porque os módulos gravam em UTC.
6. **Rastreabilidade e Dashboard:** leia as tabelas de usuários desses bancos pelo código de cada um (`rastreabilidade/app/db.py`, `dashboard/database/banco_dashboard_industrial.sql`) e aplique as mesmas regras.

### 4.4 Requisitos do script

- **Pode rodar várias vezes** sem duplicar: faz upsert pela matrícula (`INSERT ... ON CONFLICT (matricula) DO UPDATE`).
- **Roda numa transação só:** qualquer erro desfaz tudo.
- **Tem `--simular`:** faz tudo e dá rollback no final, só para ver o relatório.
- **Gera um relatório no final:** linhas lidas por origem, usuários criados ou atualizados, cada conflito de perfil ou nome com a decisão tomada, e senhas convertidas (só a matrícula, **nunca a senha**).
- **Só lê os SQLite** (abra com `sqlite3.connect("file:...?mode=ro", uri=True)`).
- **Tem testes** em `backend/tests/test_migrar_sqlite.py`, com bancos SQLite pequenos criados no próprio teste. Cubra cada regra da seção 4.3, a idempotência e o `--simular`.

**Aceite:** com os bancos do repositório, o resultado são **11 usuários** vindos de MNT + QLD (6 personas + OP-10234, OP-10235, TEC-2002, GES-0002, SVC-INTEGRACAO), mais os que só existirem em RAS ou DSH (registre o total final no Registro), e uma segunda execução não muda nada.

---

## 5. Regras gerais

- **Não altere** `rastreabilidade/`, `qualidade/`, `manutencao/`, `dashboard/` nem `portal/`. Eles são a referência do comportamento e continuam rodando na `main`.
- **Nunca faça commit** de `backend/.env`, de senhas reais nem de URLs de bancos de produção.
- **Commits:** em português, no estilo do histórico, por exemplo `feat(backend): ...`, `fix(backend): ...`, `test(backend): ...`.
- **Ao terminar:** faça push da `feature/angular`, confira se o workflow "Testes do backend (PostgreSQL)" passou no GitHub e preencha o Registro abaixo.
- **Bloqueios:** se encontrar uma decisão que não cabe a você (por exemplo, que dados usar no 4.1), registre a pergunta no Registro e siga com o que não depende dela.

---

## Registro

Cada agente acrescenta uma entrada aqui. Não apague as anteriores.

### 2026-11-10: máquina sem Docker (origem)
- Feito: fundação do `backend/` (seção 2), `docker-compose.dev.yml`, workflow de CI.
- Validado: 16 testes de unidade; fumaça das rotas com SQLite em memória; DDL do Alembic em modo offline.
- **Não validado:** nada rodou contra PostgreSQL. Os 11 testes de API foram pulados.
- Pendente: Tarefas A e B; pergunta da seção 4.1 (volumes do servidor ou arquivos do repositório).

### 2026-11-10: frontend Angular (mesma máquina, sem Docker)
- Feito: `frontend/` em **Angular 21** (o 22 exige Node ≥ 24.15; esta máquina tem 24.13). Com Node atualizado, `ng update @angular/core@22 @angular/cli@22`.
  - Login (com botões das personas demo), hub de módulos por persona, barra lateral, módulo USR completo.
  - RAS, QLD, MNT e DSH com rota protegida e tela "em construção" até a API de cada um existir.
  - `/api` vai por proxy para a porta 8000 (`frontend/proxy.conf.json`).
  - Os tokens de cor vêm de `identidade/tokens.json` via `python identidade/gerar_temas.py`, que agora também escreve `frontend/src/styles/tokens.css`.
- Validado: 23 testes Vitest (`npx ng test --watch=false`), build de produção e fluxo ponta a ponta pelo proxy, com a API rodando sobre SQLite em memória. **Não validado com Postgres** (ver o último critério da Tarefa A).
- CI novo: `.github/workflows/frontend-testes.yml`.
- Branch enviada ao GitHub. Confira na aba Actions o resultado dos dois workflows: o do backend foi a primeira execução dos testes de API contra um PostgreSQL de verdade.
