# AMATECH Smart Factory — Projeto 5: Sistema de Controle da Manutenção
## Master Prompt para Vibe Coding orientado por SDD (Spec-Driven Development)

---

### Instruções de Uso
Copie o bloco de prompt delimitado abaixo e cole diretamente na sua IDE com IA (Cursor, Windsurf, Claude Code, Antigravity, GitHub Copilot Chat ou terminal de geração). Este prompt contém todo o contexto, restrições arquiteturais, regras de negócio e contratos de API para gerar o MVP completo e funcional de ponta a ponta.

---

```markdown
# PROMPT MESTRE DE DESENVOLVIMENTO (VIBE CODING ORIENTADO POR ESPECIFICAÇÃO - SDD)

Você atuará como Engenheiro de Software Sênior especialista em Python, Streamlit, SQLite e Sistemas Industriais de Chão de Fábrica.
Sua missão é desenvolver o projeto completo **management-control** (Sistema de Controle da Manutenção da AMATECH Electronics, Projeto 5 da disciplina Ambiente Fabril I da Faculdade Matias Machline), orientado rigorosamente pela especificação técnica contida nos arquivos da pasta `docs/`.

---

## 1. CONTEXTO DO PROJETO E DOMÍNIO
- **Empresa:** AMATECH Electronics Indústria e Comércio Ltda. (Fabricante de notebooks no Polo Industrial de Manaus).
- **Problema:** Ausência de histórico de manutenção, falta de registro formal de paradas de máquina (downtime), comunicação verbal/bilhetes e falta de rastreabilidade de peças trocadas.
- **Ecossistema:** Este módulo integra um Mini-ERP composto por 4 sistemas:
  1. *Sistema de Controle de Qualidade* (Equipe Anderson - Python/SQLite/API)
  2. *Sistema de Rastreabilidade de Produtos* (Equipe Waddington - Python/Web)
  3. *Sistema de Controle da Manutenção* (Este projeto - Equipe Orlando)
  4. *Central de Visualização / Dashboard Integrador* (Equipe Letícia & Radier)
- **Identidade Visual Obrigatória:** AMATECH Corporate Design (#1F3A5F azul-escuro institucional, #2E75B6 azul de ação, #2E9E4F verde operacional, #F2B705 amarelo manutenção, #D32F2F vermelho parada).

---

## 2. REQUISITOS ARQUITETURAIS E TÉCNICOS
- **Linguagem:** Python 3.10+
- **Frontend / Aplicação:** Streamlit com componentes interativos Plotly.
- **Persistência:** SQLite (`db/manutencao.db`), usando o DDL estruturado em `docs/02_DATABASE_SCHEMA.sql`.
- **Servidor de API Integrador:** Disponibilizar endpoints REST JSON locais (FastAPI ou Flask em `api.py` ou integrado) para consumo pelos outros grupos.
- **Estrutura de Camadas:**
  - `models/`: Definição de entidades e classes de domínio.
  - `database.py`: Gerenciamento de conexão SQLite, criação automática de tabelas e execução de seed inicial se o banco não existir.
  - `services/`: Lógica de negócio isolada (`auth_service.py`, `equipamento_service.py`, `chamado_service.py`, `relatorio_service.py`).
  - `pages/` ou navegação em `app.py`: Telas limpas, fluidas, organizadas e compatíveis com uso em tablets industriais.

---

## 3. MÁQUINA DE ESTADOS E REGRAS DE NEGÓCIO OBRIGATÓRIAS
1. **Transição de Estados:**
   - Operador abre chamado -> Máquina passa para `PARADA` (Vermelho) e Chamado status `ABERTO`. Timestamp `data_hora_abertura = now()`.
   - Técnico clica em "Assumir OS" -> Máquina passa para `EM_MANUTENCAO` (Amarelo) e Chamado status `EM_ANDAMENTO`. Timestamp `data_hora_inicio_atendimento = now()`.
   - Técnico preenche diagnóstico + causa raiz + peças e clica em "Concluir OS" -> Máquina volta para `OPERACIONAL` (Verde) e Chamado status `CONCLUIDO`. Timestamp `data_hora_fim_atendimento = now()`.
2. **Cálculo Automático de Downtime (RN05):**
   `downtime_minutos = round((fim - abertura).total_seconds() / 60)`. Gravado no banco e imutável pelo usuário.
3. **Bloqueio de Redundância (RN02):**
   Se uma máquina já estiver `PARADA` ou `EM_MANUTENCAO`, proibir nova abertura de chamado e exibir alerta com o número da OS ativa.
4. **Controle de Acesso por Perfil (RBAC):**
   - `OPERADOR`: visualiza Painel de Máquinas e Abertura de Chamado.
   - `TECNICO`: visualiza Painel de Máquinas, Fila de Chamados, Atendimento de OS e Histórico.
   - `GESTOR`: visualiza todas as telas, incluindo Dashboard de Indicadores Industriais (MTTR, MTBF, Downtime) e Cadastros.
5. **Trilha de Auditoria (RN08):**
   Toda alteração de status de máquina deve inserir um registro na tabela `historico_status`.

---

## 4. ESPECIFICAÇÃO DAS TELAS DA APLICAÇÃO
1. **Login:** Acesso por Matrícula e Senha (com contas demo pré-carregadas para facilitar testes rápidos: Operador `OP-10234`, Técnico `TEC-2001`, Gestor `GES-0001`).
2. **Painel de Máquinas:** Grid de cards com status colorido, nome, posto e botão rápido "Abrir Chamado". Atualização automática a cada 5–10s.
3. **Abertura de Chamado:** Seleção de máquina (com autopreenchimento de setor e posto), prioridade (Baixa, Média, Alta, Crítica) e descrição da falha.
4. **Fila de Chamados (Técnico):** Listagem de chamados abertos ordenada por prioridade com botão de ação direta "Assumir OS".
5. **Ordem de Serviço (Técnico):** Cronômetro em tempo real do tempo de atendimento, campos de diagnóstico e causa raiz, adicionar/remover peças substituídas e botão "Concluir OS".
6. **Dashboard Gerencial:** Cards com KPIs industriais (Downtime total, MTTR, MTTA, Disponibilidade %) e gráficos Plotly (Ranking de gargalos por máquina, Causas-raiz, Chamados por setor).
7. **Histórico:** Tabela filtrável com exportação em 1 clique para CSV.
8. **Cadastros:** Formulários de inclusão e inativação lógica de Equipamentos, Peças e Usuários.

---

## 5. API DE INTEGRAÇÃO (REST JSON)
Crie um arquivo `api.py` com servidor FastAPI/Flask expondo:
- `GET /api/status` -> `{"sistema": "Controle da Manutencao", "status": "online"}`
- `GET /api/equipamentos` -> Lista de máquinas com status operacional.
- `GET /api/manutencao/chamados` -> Lista de todas as OSs com timestamps, downtime e peças.
- `GET /api/manutencao/indicadores` -> Resumo consolidado de MTTR, Downtime total e contadores.

---

## 6. INSTRUÇÕES DE ENTREGA DO CÓDIGO
- Gere código modular, limpo, documentado com docstrings e tipos.
- Não use bibliotecas externas desnecessárias além de `streamlit`, `pandas`, `plotly`, `sqlite3` (nativa) e opcionalmente `fastapi` / `uvicorn`.
- Crie um arquivo `init_db.py` ou rotina automática no início da aplicação para criar o banco SQLite com dados de demonstração da AMATECH a partir do script `docs/02_DATABASE_SCHEMA.sql`.
- Garanta que a aplicação inicialize sem falhas executando: `streamlit run app.py`.
```
