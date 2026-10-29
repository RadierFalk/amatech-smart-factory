# Integração do ecossistema AMATECH Smart Factory: alterações por setor

**OA3 · 28/10/2026.** Este resumo explica a cada equipe o que mudou no sistema dela para os quatro projetos conversarem
(enunciado, seção 1.2: "ausência de integração entre setores"). As alterações vieram do branch **`integracao-ecossistema`**
de cada repositório original (o Dashboard, do branch `mvp`). Nada foi apagado nem mudou de comportamento para quem usa as telas como antes. Os testes que já
existiam continuam passando.

## Visão geral

Cada sistema mantém o seu banco e conversa com os outros **só pelas APIs**. Ninguém lê o banco de ninguém.

```
            números de série, etapas                      defeitos
 Rastreabilidade (8000) ◄─────────────── Qualidade (5000 / tela 8502) ──────────────┐
        │       ▲          reprovado / reprocesso / aprovado     │                  │
        │       └────────────────────────────────────────────────┘                  │
        │                                         chamado (defeito da máquina)       │
        │                                Manutenção (5002 / tela 8503) ◄────────────┤
        │ produção                              │ paradas                             │
        ▼                                       ▼                                     │
                        Dashboard Industrial (8501) ◄─────────────────────────────────┘
```

| Sistema | API | Tela | Rota no servidor | Dono dos cadastros |
| --- | --- | --- | --- | --- |
| Rastreabilidade (Projeto 2) | 8000 | 8000 | `/rastreabilidade/` | Modelos de notebook e números de série |
| Controle da Qualidade (Projeto 4) | 5000 | **8502** | `/qualidade/` | Ocorrências de defeito |
| Controle da Manutenção (Projeto 5) | 5002 | **8503** | `/manutencao/` | Máquinas (TAGs) |
| Dashboard Industrial (Projeto 3) | **5003** (nova) | 8501 | `/dashboard/` | Estações, turnos e indicadores |

As portas das telas foram fixadas (`.streamlit/config.toml`) para os quatro rodarem juntos no mesmo computador. No
servidor da rede, todos ficam no mesmo IP, cada um na sua rota (veja a última seção e o `SERVIDOR.md`).

### Chaves de demonstração

| Quem chama | Quem recebe | Cabeçalho `X-API-Key` |
| --- | --- | --- |
| Qualidade | Rastreabilidade | `amt_demo_qualidade` |
| Dashboard | Rastreabilidade | `amt_demo_dashboard` |
| Manutenção (reservada) | Rastreabilidade | `amt_demo_manutencao` |
| Qualidade | Manutenção (abrir chamado) | `amatech-manutencao-demo` |

São chaves só para a demonstração, como a `amatech-iot-demo` que já existia. Todas podem ser trocadas por variáveis de
ambiente (detalhes em cada seção).

### Identificador comum

Todo dado enviado a outro sistema leva **`origem_sistema` + `id_externo`** (ex.: `qualidade` + `QLD-15`). Assim, um reenvio
**atualiza ou é ignorado, nunca duplica**. Padrões: `QLD-<id da ocorrência>`, `MNT-<id do chamado>` e
`AAAA-MM-DD|<turno>|<modelo>` (produção agregada no Dashboard).

---

## Rastreabilidade (`rastreabilidade/`)

**O que mudou**

1. **Nova rota `GET /api/v1/passagens?de=&ate=&status=&limite=`**: devolve o histórico de etapas de todas as produções no
   período (`de` e `ate` em ISO 8601, UTC). Ao contrário da fila `/eventos`, inclui o histórico de demonstração do
   povoamento inicial. O Dashboard usa essa rota para contar Aprovados e Reprovados por turno.
2. **`POST /api/v1/producoes/{serie}/status` aceita `descricao_falha`, `motivo_reprovacao` e `id_externo`** (todos
   opcionais). Ao reprovar, a não conformidade usa a falha real em vez do texto fixo "Reprovado automaticamente pela
   máquina" e grava `origem_sistema` e `id_externo`. Uma reprovação com o mesmo `id_externo` não é aplicada de novo
   (`"alterado": false`). Sem esses campos, tudo funciona como antes.
3. **Chaves de demonstração** `qualidade`, `dashboard` e `manutencao`, criadas ao iniciar **somente se o nome ainda não
   existir** (um cliente já cadastrado nunca é alterado). `AMATECH_CHAVES_DEMO=0` desliga;
   `AMATECH_CHAVE_QUALIDADE`, `AMATECH_CHAVE_DASHBOARD` e `AMATECH_CHAVE_MANUTENCAO` trocam as chaves.

**Arquivos:** `app/config.py`, `app/db.py`, `app/schemas.py`, `app/routers/integracao.py`, `app/servicos/integracao.py`,
`app/servicos/producao.py`, `tests/test_api.py`, `docs/INTEGRACAO.md`.

**Testes:** 37 passando (os 33 originais e 4 novos na classe `TestEcossistema`). Na classe `TestIntegracao` foi
acrescentada uma linha que desliga as chaves de demonstração, porque esses testes criam as próprias chaves `qualidade`
e `manutencao`.

```bash
python -m pytest -q
curl -H "X-API-Key: amt_demo_dashboard" "http://localhost:8000/api/v1/passagens?status=Aprovado"
```

---

## Controle da Qualidade (`qualidade/`)

**O que mudou**

1. **Novo `integracao.py`**, com tempo limite em toda chamada. **Se um sistema estiver fora do ar, a Qualidade continua
   funcionando** e só mostra um aviso.
   - Ao abrir o sistema (e no botão *Atualizar cadastros dos setores*, na barra lateral), busca os notebooks na
     Rastreabilidade e as máquinas na Manutenção. Só acrescenta o que falta.
   - Ao **registrar uma ocorrência**, avisa a Rastreabilidade conforme a situação do produto:
     **Reprovado** → etapa *Reprovado*, com a observação como falha e o tipo de defeito como motivo;
     **Em_reprocesso** → *Reprovado* e, em seguida, *Em Montagem*;
     **Aprovado** → *Aprovado*, se o notebook ainda não tiver passado por essa etapa.
   - Nova opção no formulário: **Abrir chamado na manutenção (defeito causado pela máquina)**. A prioridade vem da
     classificação: Crítico → CRITICA, Maior → ALTA, Menor → MEDIA.
2. **API: filtros `?de=AAAA-MM-DD&ate=AAAA-MM-DD`** em `GET /api/ocorrencias`.
3. **Cadastros alinhados com os donos**: as séries passaram a ser `AMT-000001` a `AMT-000030` (modelos AMT N14 a N18, os
   mesmos da Rastreabilidade), e as máquinas, as TAGs da Manutenção (acrescentadas SMT-02, SMT-03, TEST-03 e EMB-01).
   O `criar_banco.py` foi ajustado. O `banco/controle_qualidade.db` do repositório **foi atualizado no lugar, sem
   recriar**: as 39 ocorrências existentes foram mantidas e continuam ligadas aos mesmos produtos (AMT-NB001 virou
   AMT-000001, e assim por diante).
4. `requests` no `requirements.txt`; tela fixada na porta **8502** (a API continua na 5000).

**Arquivos:** `integracao.py` (novo), `app.py`, `api.py`, `banco.py`, `criar_banco.py`, `telas/registro_ocorrencia.py`,
`banco/controle_qualidade.db`, `requirements.txt`, `.streamlit/config.toml`, `tests/test_integracao.py` (novo),
`README.md` (seção 9).

**Variáveis de ambiente:** `RASTREABILIDADE_URL`, `RASTREABILIDADE_CHAVE`, `MANUTENCAO_URL`, `MANUTENCAO_CHAVE` e
`INTEGRACAO_TEMPO_LIMITE`.

**Testes:** o projeto não tinha testes. Foram criados 6, com respostas HTTP simuladas, que rodam sem os outros sistemas
no ar, e mais 4 da API em FastAPI (`tests/test_api.py`): 10 passando, `python -m pytest tests -q`.

---

## Controle da Manutenção (`manutencao/`)

**O que mudou**

1. **Nova rota `POST /api/manutencao/chamados`** (cabeçalho `X-API-Key`, variável `MANUTENCAO_API_KEY`, padrão
   `amatech-manutencao-demo`). Outro sistema abre um chamado pela TAG da máquina:
   `{"equipamento_tag", "descricao_falha", "prioridade", "tipo_manutencao", "origem_sistema", "id_externo"}`.
   Usa o mesmo `abrir_chamado` da tela, então valem as mesmas regras. Respostas: 201 (aberto), 200 com `"criado": false`
   (reenvio), 401 (chave), 404 (TAG não existe), **409 (máquina já parada ou em manutenção, RN02)** e 422 (dados
   inválidos).
2. **Usuário de serviço "Integração (outros sistemas)"** (matrícula `SVC-INTEGRACAO`, perfil OPERADOR, **inativo**, não
   faz login): fica como operador de abertura desses chamados, porque o campo é obrigatório.
3. **Migração automática e idempotente** em `ensure_database_initialized()`, aplicada também a bancos antigos, sem apagar
   nada: colunas `origem_sistema` e `id_externo` em `chamados_manutencao` (com índice único), máquinas **INS-01**
   (Inserção Manual) e **QC-01** (Inspeção da Qualidade), que a Qualidade usa, e o usuário de serviço. O
   `docs/02_DATABASE_SCHEMA.sql` e o `manutencao.db` do repositório já estão atualizados.
4. `GET /api/manutencao/chamados`: as datas agora terminam em **"Z"** (o banco sempre gravou em UTC; o "Z" deixa isso
   explícito), e cada chamado traz `origem_sistema` e `id_externo`.
5. `MANUTENCAO_DB` permite trocar o caminho do banco; tela fixada na porta **8503** (o tema não foi alterado).

**Arquivos:** `api.py`, `config.py`, `database.py`, `services/chamado_service.py`, `docs/02_DATABASE_SCHEMA.sql`,
`manutencao.db`, `.streamlit/config.toml`, `tests/test_integracao_ecossistema.py` (novo),
`docs/06_INTEGRACAO_ECOSSISTEMA.md` (seção 4).

**Testes:** 11 passando (os 7 originais e 4 novos).

```bash
python -m pytest -q
curl -X POST -H "X-API-Key: amatech-manutencao-demo" -H "Content-Type: application/json" \
     -d '{"equipamento_tag":"EMB-01","descricao_falha":"Teste de integração","origem_sistema":"teste","id_externo":"T-1"}' \
     http://localhost:5002/api/manutencao/chamados
```

---

## Dashboard Industrial (`dashboard/`)

Para buscar dados, o Dashboard só **consome** as APIs. Na tela **Importação**, a seção *Sincronizar com os setores*:

| Busca em | Vira | Regras |
| --- | --- | --- |
| Rastreabilidade: `/api/v1/produtos`, `/api/v1/passagens` | Modelos e produção por dia, turno e modelo | Cada Aprovado ou Reprovado é uma unidade: realizada = aprovados + reprovados |
| Qualidade: `/api/ocorrencias?de=&ate=` | Defeitos (quantidade 1 cada) | Em_reprocesso também gera retrabalho na Montagem final |
| Manutenção: `/api/equipamentos`, `/api/manutencao/chamados` | Máquinas e paradas | Da abertura ao fim do atendimento; CORRETIVA = Falha de equipamento, PREVENTIVA = Manutenção programada; cancelados não contam |

Cada setor é gravado como uma importação: **um registro inválido recusa só aquele setor** (RN06). Horários em UTC são
convertidos para Manaus (UTC-4). Eventos fora dos turnos (06h–14h e 14h–22h) aparecem como ignorados, e sistema fora
do ar aparece como aviso. A correspondência de nomes entre os sistemas (ex.: "Testes Funcionais" = "Teste funcional")
está em `docs/CADASTROS_COMUNS.md`.

**Testes:** 51 passando, incluindo os 5 da API nova (`python -m pytest testes -q`).

---

## Como testar os quatro juntos

No servidor: `docker compose up -d --build` (veja o `SERVIDOR.md`). No próprio computador, sem Docker:
`powershell -ExecutionPolicy Bypass -File iniciar.ps1`, na raiz do repositório, sobe as telas e as APIs (veja o
`README.md`). Ou, à mão, cada comando num terminal, a partir da pasta de cada projeto:

```bash
# Rastreabilidade (API e telas em http://localhost:8000)
python -m uvicorn app.main:app --port 8000
# Manutenção: API na 5002 e tela em http://localhost:8503
python -m uvicorn api:app --port 5002
streamlit run app.py
# Qualidade: API na 5000 e tela em http://localhost:8502
python -m uvicorn api:app --port 5000
streamlit run app.py
# Dashboard: API na 5003 e tela em http://localhost:8501 (login supervisor / super123)
python -m uvicorn api:app --port 5003
streamlit run app.py
```

Roteiro de demonstração:

1. Na **Qualidade**, registre uma ocorrência *Reprovado* para um notebook (ex.: AMT-000017), com a opção de abrir
   chamado marcada.
2. Na **Rastreabilidade**, o notebook aparece como *Reprovado*, com a falha informada.
3. Na **Manutenção**, a máquina da ocorrência fica *PARADA*, com um chamado aberto pela "Integração".
4. No **Dashboard** → Importação → *Sincronizar agora*. No Painel, a produção, os defeitos e a parada em andamento
   aparecem nos indicadores.

**Atenção a um limite da regra RN06 no Dashboard.** Um defeito só é aceito se houver produção (Aprovado ou Reprovado na
Rastreabilidade) no mesmo dia, turno e modelo. Uma ocorrência registrada com hora muito diferente do momento real faz o
Dashboard recusar todos os defeitos daquele período. A tela mostra qual linha causou a recusa.

---

## Etapa 2: servidor da rede (Docker)

Para todos na mesma rede usarem os sistemas, como numa empresa: **um servidor Windows com Docker, um IP fixo e uma rota
para cada sistema**, atrás de um proxy (Caddy) na porta 80. Guia completo em `SERVIDOR.md`.

| Rota | Telas | API (FastAPI) |
| --- | --- | --- |
| `http://IP/rastreabilidade/` | Rastreabilidade | `/rastreabilidade/api/v1/...` |
| `http://IP/qualidade/` | Qualidade | `/qualidade/api/...` |
| `http://IP/manutencao/` | Manutenção | `/manutencao/api/...` |
| `http://IP/dashboard/` | Dashboard | `/dashboard/api/...` |

O que mudou em cada sistema para isso:

| Sistema | Mudança |
| --- | --- |
| Todos | Cada **API roda num processo próprio**, separado da tela. Antes, as APIs da Qualidade e da Manutenção subiam numa thread do Streamlit e só existiam depois que alguém abria a tela. Cada API tem documentação em `/docs` |
| Rastreabilidade | As telas resolvem os endereços da API a partir da rota em que estão publicadas (funcionam em `/` e em `/rastreabilidade/`) |
| Qualidade | API migrada de **Flask para FastAPI**; `/api/ocorrencias` exige a chave `QUALIDADE_API_KEY`; banco configurável (`QUALIDADE_DB`), começando com uma cópia do banco do projeto |
| Manutenção | Os `GET` também exigem a chave `MANUTENCAO_API_KEY`; CORS só para as origens de `MANUTENCAO_CORS` (antes, `*`) |
| Dashboard | **API nova** (porta 5003): `/api/indicadores`, `/api/graficos` e `/api/paradas-em-andamento`, com a cor do semáforo; chave `DASHBOARD_API_KEY`. O conector envia as chaves da Qualidade e da Manutenção |

Arquivos novos na raiz: `Dockerfile` (uma imagem para os quatro), `docker-compose.yml` (8 contêineres: o proxy, a
Rastreabilidade e a tela e a API de cada um dos outros três), `servidor/Caddyfile` (as rotas), `servidor/portal/`
(página inicial), `.env.exemplo` (as chaves) e `SERVIDOR.md`.

| Chave (`X-API-Key`) | Variável no `.env` | Padrão de demonstração |
| --- | --- | --- |
| Qualidade e Dashboard → Rastreabilidade | `RASTREABILIDADE_CHAVE_QUALIDADE`, `RASTREABILIDADE_CHAVE_DASHBOARD` | `amt_demo_qualidade`, `amt_demo_dashboard` |
| → API da Qualidade | `QUALIDADE_API_KEY` | `amatech-qualidade-demo` |
| → API da Manutenção | `MANUTENCAO_API_KEY` | `amatech-manutencao-demo` |
| → API do Dashboard | `DASHBOARD_API_KEY` | `amatech-dashboard-demo` |
