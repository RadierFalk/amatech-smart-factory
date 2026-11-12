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
python -m pytest -q -rs                               # esperado: todos passando, 0 skipped (42 em 2026-11-10)
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

### 4.2 Escopo agora: `usr.usuarios` e `mnt.*`

Já existem no `backend/` os modelos de `usr` e `mnt` (migrações `0001` e `0002`). Os de `ras`, `qld` e `dsh` ainda não, a não ser que o Registro diga o contrário. Implemente `migrar_usr` e `migrar_mnt` e deixe o script organizado em uma função por schema, para os outros entrarem quando o modelo deles existir. `migrar_usr` **devolve o mapa `(origem, id_antigo) -> usr.usuarios.id`**, que `migrar_mnt` usa nas FKs de usuário.

**De `manutencao/manutencao.db` para `mnt` (modelos em `backend/app/modulos/manutencao/modelos.py`):**

| SQLite antigo | PostgreSQL novo | Cuidados |
|---|---|---|
| `usuarios` | `usr.usuarios` | Pelo mapa de `migrar_usr` (seção 4.3). A tabela não existe mais em `mnt`. |
| `equipamentos` | `mnt.equipamentos` | Mesmas colunas. `codigo_tag` em maiúsculas (há CHECK). `ativo` 0/1 vira boolean. |
| `pecas` | `mnt.pecas` | Mesmas colunas. `codigo_peca` em maiúsculas (há CHECK). |
| `chamados_manutencao` | `mnt.chamados` | `operador_abertura_id` e `tecnico_responsavel_id` passam pelo mapa de usuários. Datas texto (UTC) viram `timestamptz`. **Cancelados:** o sistema antigo gravava o motivo em `diagnostico_tecnico`; mova para `motivo_cancelamento` e deixe `diagnostico_tecnico` nulo. `origem_sistema` em minúsculas. |
| `chamado_pecas_trocadas` | `mnt.chamado_pecas` | Agora há **UNIQUE (chamado_id, peca_id)**: some as quantidades de linhas repetidas da mesma peça na mesma OS (a conclusão antiga podia duplicar). |
| `historico_status` | `mnt.historico_status` | `usuario_id` pelo mapa de usuários. Mantenha também as linhas em que `status_anterior = status_novo` (o sistema novo não grava mais essas, mas são histórico). |

- **Preserve os IDs** de equipamentos, peças e chamados: o número da OS aparece para as pessoas ("OS #3"). Depois de inserir com IDs explícitos, ajuste as sequências: `SELECT setval(pg_get_serial_sequence('mnt.chamados', 'id'), (SELECT max(id) FROM mnt.chamados))`, e o mesmo para as outras tabelas.
- **RN02 no banco:** o índice `ux_chamados_uma_os_ativa` recusa duas OS ativas na mesma máquina. Se o banco antigo tiver esse caso, o script não pode falhar no meio: coloque no relatório e pergunte ao dono do projeto qual manter.
- **Aceite do `mnt`:** contagem de linhas igual à origem em cada tabela, exceto `chamado_pecas` quando houver linhas somadas (o relatório diz quantas). Depois da migração, `GET /api/mnt/indicadores` (logado como GES-0001) dá o mesmo total de chamados que a tela antiga de Indicadores.

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

### 2026-11-10: módulo de Manutenção (mesma máquina, sem Docker)
- Feito no backend:
  - `app/modulos/manutencao/` com modelos, regras, cadastros, indicadores e 20 rotas em `/api/mnt`;
  - migração `0002` com as tabelas `mnt`;
  - `scripts/seed_demo.py` povoa também as 10 máquinas e as 7 peças.
- Feito no frontend: `src/app/modulos/manutencao/` com painel, abrir chamado, meus chamados, fila, ordens de serviço, preventivas, indicadores (gráficos em `src/app/shared/graficos.ts`), histórico com CSV, cadastros e auditoria.
- **Testes sem Docker:** o `tests/conftest.py` agora cai para SQLite em memória quando não acha o Postgres e `AMATECH_TEST_DATABASE_URL` não está definida.
  - Isso valida as regras de negócio localmente; não substitui o Postgres.
  - O CI define a variável e continua exigindo 0 skipped.
  - Testes que só fazem sentido no Postgres usam `@pytest.mark.postgres`.
- **Validado:**
  - 42 testes do backend (no SQLite) e 30 do frontend;
  - DDL das migrações em modo offline;
  - roteiro no navegador (Edge headless, API sobre SQLite) com operador → técnico → supervisor, sem erros de console ou de API e sem rolagem horizontal no celular.
- **Não validado:** nada contra o Postgres. Pontos para conferir na Tarefa A:
  - `alembic check` com a `0002`;
  - a trava `SELECT ... FOR UPDATE OF chamados` (o SQLite ignora `FOR UPDATE`);
  - o índice parcial `ux_chamados_uma_os_ativa` sob concorrência real (duas aberturas simultâneas na mesma máquina devem resultar em uma 201 e uma 409).
- Achado para o módulo DSH: a paleta categórica de `identidade/tokens.json` (`grafico-1..4`) **falha** no validador de paleta da skill de dataviz (`grafico-1` e `grafico-2` têm ΔE 14,9 em visão normal; `grafico-2` tem pouca saturação). Os gráficos de MNT usam uma série só e não são afetados. Corrija a paleta antes de fazer gráficos com várias séries.

### 2026-11-12: Tarefa B, migração de `usr` e `mnt` (máquina sem Docker)
- Antes de começar: o CI do commit `4a5a007` já roda no Postgres de verdade (`alembic upgrade head`, `alembic check` sem diferenças, **42 passed, 0 skipped**). Da Tarefa A ainda falta o que o CI não cobre: `downgrade base` + `upgrade head`, acentos no banco, ponta a ponta no navegador e as duas aberturas simultâneas.
- Feito: `backend/scripts/migrar_sqlite.py` (`migrar_usr`, `migrar_mnt`, `--simular`, uma transação, upsert, `setval` das sequências) e `backend/tests/test_migrar_sqlite.py` (24 testes: cada regra da 4.3, mnt, RN02, idempotência, `--simular`, origem ausente, bancos do repositório).
- Resultado com os bancos do repositório (MNT + QLD; portal, RAS e DSH não existem no Git): **11 usuários**, os 5 conflitos de perfil da tabela 4.3, 4 senhas em texto puro convertidas, `SVC-INTEGRACAO` sem login. `mnt`: 10 máquinas, 7 peças, 4 chamados, 2 peças trocadas (nenhuma somada), 12 linhas de histórico. Nenhuma OS ativa em duplicidade. Segunda execução: nada muda.
- Decisões tomadas e que valem conferência:
  - Sem o banco do portal, nome e perfil das 6 personas vêm de `seed_demo.PERSONAS` (o portal gera os mesmos dados).
  - O Dashboard grava `criado_em` em hora local (`datetime('now','localtime')`): convertido de UTC-4 para UTC, e não tratado como UTC.
  - Hashes PBKDF2 (RAS e DSH) são mantidos como estão: essas contas ficam sem login até alguém redefinir a senha pelo módulo USR. O relatório lista as matrículas.
  - RN02 na origem: fica a OS ativa mais antiga, e as outras (com o histórico delas) ficam fora e vão para "PENDÊNCIAS".
  - O destino precisa estar vazio em `mnt` ou ter os mesmos IDs: se o `seed_demo` já rodou com outros IDs, o script recusa e não grava nada.
- Validado: 66 testes do backend no SQLite local. **Não validado no Postgres**: a execução real do script (o CI roda os testes novos no Postgres no próximo push) e o aceite `GET /api/mnt/indicadores` comparado com a tela antiga.
- **Perguntas para o dono do projeto:**
  1. (continua aberta) Migrar dos volumes `dados-*` do servidor ou dos arquivos do repositório?
  2. O Dashboard não tem matrícula: o login (`admin`, `supervisor`...) vira a matrícula (`ADMIN`, `SUPERVISOR`). A Rastreabilidade usa `MAT-xxxx`. Se forem as mesmas pessoas das personas (ex.: `MAT-0001` = `ADM-0001`), é preciso uma tabela de equivalência de matrículas; sem ela, viram usuários separados.

### 2026-11-12: módulo de Qualidade (QLD) na API única e no Angular (máquina sem Docker)
- Feito no backend:
  - `app/modulos/qualidade/` com modelos, serviço, indicadores e 13 rotas em `/api/qld`; migração `0003` com as tabelas `qld`.
  - Máquinas vêm de `mnt.equipamentos` (a tabela `maquina` da QLD guardava só a TAG). Notebooks ficam em `qld.produtos` até a RAS entrar na API única.
  - Data e hora digitadas (hora de Manaus) viraram `ocorrida_em` (timestamptz, UTC). Valores em códigos (`CRITICO`, `EM_REPROCESSO`, `EM_ANALISE`); `visibilidade` virou `oculta`.
  - "Abrir chamado na manutenção" chama `servico_mnt.abrir_chamado_por_tag` dentro da mesma transação, num savepoint: se a MNT recusar (RN02), a ocorrência é gravada e a recusa vira aviso. Dá para abrir o chamado depois (`POST /api/qld/ocorrencias/{id}/chamado`). O vínculo é `origem_sistema='qualidade'` + `id_externo='QLD-<id>'`, como no sistema antigo.
  - Permissões: a matriz de `qualidade/permissoes.py`, com o **Supervisor igual ao Inspetor** (não existia na QLD; o GES-0001 era Administrador lá). Técnico continua sem acesso ao módulo (`rbac.py`).
  - **Não portado:** o aviso à Rastreabilidade (mudar a etapa do notebook). Entra quando a RAS existir na API única.
  - `seed_demo` povoa também estações, tipos de defeito e 30 notebooks.
- Script de migração: `migrar_qld` (IDs preservados; TAG -> `mnt.equipamentos`; recusa tudo se uma TAG usada não existir na MNT), `--equivalencias arquivo.csv` (`matricula_antiga,matricula_nova`) e a lista de **possíveis duplicados** (mesmo nome, matrículas diferentes; só avisa).
- Feito no frontend: `src/app/modulos/qualidade/` com painel (indicadores e gráficos), registrar/editar ocorrência, histórico (busca, filtros, ocultar, abrir chamado, CSV) e cadastros. Nova variante global `.aviso.atencao`.
- Validado:
  - 89 testes do backend (SQLite local) e 40 do frontend; build de produção;
  - aceite com os dados reais: migrando os bancos do repositório, `/api/qld/indicadores` dá os mesmos números da tela antiga (38 visíveis, 6 abertas, 7 notebooks reprovados, contagens por estação, tipo e dia idênticas).
- **Não validado:** no Postgres (o CI roda no push) e no navegador (não houve roteiro ponta a ponta desta vez).

### 2026-11-12: módulo de Rastreabilidade (RAS) na API única e no Angular (máquina sem Docker)
- CI do commit `dbe6ed5` (QLD) passou no Postgres: `alembic check` sem diferenças, 89 passed, 0 skipped.
- Feito no backend:
  - `app/modulos/rastreabilidade/` com etapas, componentes, modelos com a lista de componentes (BOM), produções, passagens de etapa, não conformidades, solicitações e baixas de material, painel e 4 relatórios: 30 rotas em `/api/ras`; migração `0004` (schema `ras`).
  - Nomes novos: produtos -> `modelos`, status_producao -> `etapas`, historico_passagem -> `passagens`, solicitacoes_materiais -> `solicitacoes`, baixas_materiais -> `baixas`.
  - Regras portadas: nº de série `AMT-<id>` e ID único com o dia da fábrica; reprovar exige falha e motivo e gera não conformidade; próxima etapa sugerida (de Parado/Reprovado volta para a 2ª etapa); solicitação PENDENTE -> PARCIAL -> ATENDIDA; baixa limitada ao saldo e ao estoque, com o componente travado (`FOR UPDATE`); alterar/excluir baixa devolve ao estoque.
  - **Permissões:** no sistema antigo quase tudo era liberado para qualquer usuário logado. Agora: produção (criar, mudar etapa, NC) = Operador, Inspetor, Supervisor, Adm.; excluir produção = Supervisor, Adm.; solicitar material = Operador, Almoxarife, Supervisor, Adm.; baixa = Almoxarife, Adm. (como antes); componentes = Almoxarife, Supervisor, Adm.; modelos e etapas = Supervisor, Adm.
  - Máquinas/IoT: `POST /api/ras/maquinas/status` com `X-API-Key` (`AMATECH_CHAVE_MAQUINAS`, obrigatória em produção), assinado pela conta de serviço `SVC-INTEGRACAO`.
  - **Não portado (de propósito):** a API externa `/api/v1`, a fila de eventos e as chaves por sistema. Na API única os módulos se chamam por dentro.
  - **QLD -> RAS:** registrar uma ocorrência leva o resultado à produção do mesmo nº de série (Reprovado / reprocesso volta para Em Montagem / Aprovado se ainda não passou), num savepoint como o chamado da MNT. Correção em relação ao antigo: se o notebook **já estava Reprovado**, a não conformidade da Qualidade é gravada assim mesmo (o antigo descartava a falha e dizia que tinha reprovado).
  - Os notebooks da QLD continuam em `qld.produtos`, ligados à RAS pelo nº de série. **Pendente:** apontar `qld.ocorrencias` para `ras.producoes` (exige migrar a QLD junto com a RAS).
  - `seed_demo` povoa a RAS (as 30 produções de demonstração do sistema antigo, com histórico e materiais) e cria a conta de serviço.
- Script de migração: `migrar_ras` (IDs preservados; datas da RAS em UTC; NC com origem 'AMATECH' vira origem vazia) e a equivalência padrão `MAT-IOT -> SVC-INTEGRACAO`.
- Frontend: `src/app/modulos/rastreabilidade/` com painel (atualiza a cada 30 s), produções, ficha do notebook (mudar etapa, NC, materiais, histórico), materiais (solicitações e baixas), relatórios com CSV e cadastros. Correção global em `styles.scss`: `.pagina` com `grid-template-columns: minmax(0, 1fr)` (os formulários em grade estouravam a tela no celular, inclusive nos módulos antigos).
- Validado:
  - 106 testes do backend (SQLite local) e 46 do frontend; build de produção; nomes das 47 constraints/índices da `0004` iguais aos dos modelos (comparação do DDL offline).
  - Migração com um banco da RAS gerado pelo seed do sistema antigo: contagens iguais em todas as tabelas, e o painel e os 4 relatórios da API nova dão os mesmos números do código antigo.
  - **Roteiro no navegador** (Edge sem interface, API sobre SQLite com o seed): telas de QLD e RAS por persona, fluxo QLD -> RAS -> MNT pela tela (ocorrência reprova o notebook e abre a OS), iniciar produção / mudar etapa / solicitar material / dar baixa, sem rolagem horizontal da página em 11 telas no celular, 0 erros de console ou de API.
- **Não validado:** no Postgres (o CI roda no push).

### 2026-11-12: módulo do Dashboard (DSH) na API única e no Angular (máquina sem Docker)
- CI do commit `678ec33` (RAS) passou no Postgres: `alembic check` sem diferenças com a `0004`, 106 passed, 0 skipped.
- **Decisão do dono do projeto:** o DSH calcula os indicadores **direto dos módulos**, sem cópias. Antes ele sincronizava produção, defeitos e paradas por HTTP para tabelas próprias; agora:
  - produção = passagens da RAS pelas etapas Aprovado e Reprovado (realizada = aprovada + reprovada, como na sincronização antiga);
  - retrabalho e defeitos por estação = ocorrências visíveis da QLD (retrabalho = Em reprocesso);
  - paradas = chamados da MNT não cancelados (ativos contam até agora; preventiva que ainda não parou a máquina não conta);
  - o DSH guarda só o que é dele: `dsh.turnos`, `dsh.limites` (semáforo), `dsh.metas`, `dsh.tipos_perda`, `dsh.perdas` (migração `0005`).
  - Saíram o lançamento manual e o CSV de produção, defeitos e paradas, e a API externa `/api/indicadores` (os módulos consultam por dentro). Ficaram lançamento e CSV (tudo ou nada, RN06) de **metas e perdas**.
- Fórmulas, turnos (06–14, 14–22) e limites do semáforo iguais ao antigo; eventos fora dos turnos ficam de fora. Teste do **caso de referência do enunciado** (meta 1.500, 1.420 produzidos, 60 reprovados, 85 min de parada) dá 94,7% / 4,2% / 215,7 un/h.
- Permissões: painel e histórico para todos com acesso ao DSH (inclui o Técnico); metas, perdas, planilhas, turnos, tipos de perda e limites = Supervisor e Administrador (no antigo, o Supervisor).
- `seed_demo`: turnos, limites, tipos de perda e metas/perdas de demonstração calculadas sobre a produção de demonstração da RAS.
- Script de migração: `migrar_dsh` traz turnos (unidos pelo nome), limites, tipos de perda, metas e perdas. Produto do DSH antigo vira o modelo da RAS de mesmo nome ou código; estação vira a da QLD (com sinônimos, ex.: "Linha SMT" = "SMT"). O que não casa vai para "ignorados", e o relatório lembra que produção/defeitos/paradas do DSH antigo não são migrados (eram cópias).
- **Paleta dos gráficos:** nenhum gráfico do ERP usa mais de uma série. "Produção × meta" virou barra realizada + **traço de referência** em tinta neutra (componente `BarrasHorizontais`, entrada `rotuloReferencia`), em vez de duas barras com cores categóricas. A paleta `grafico-1..4` continua reprovada no validador da skill de dataviz e **precisa ser corrigida antes do primeiro gráfico com várias séries**.
- Frontend: `src/app/modulos/dashboard/` com painel (filtro de período/turno/modelo numa linha, 6 indicadores com semáforo em texto, máquinas paradas agora, 6 gráficos), histórico com CSV, metas e perdas (com importação e planilha modelo) e configuração. A tela "em construção" foi removida: os 5 módulos existem.
- Validado: 120 testes do backend (SQLite local) e 53 do frontend; build de produção; nomes, colunas e CHECKs da `0005` iguais aos dos modelos (DDL offline); migração com o banco gerado pelo SQL do DSH antigo; **roteiro no navegador** com as telas dos 4 módulos por persona, fluxo QLD -> RAS -> MNT -> DSH (a OS aberta pela Qualidade aparece no painel do DSH como máquina parada), meta gravada pela tela e vista no painel, 14 telas sem rolagem horizontal no celular, 0 erros de console ou de API.
- **Não validado:** no Postgres (o CI roda no push).
