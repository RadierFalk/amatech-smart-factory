# AMATECH Smart Factory — Projeto 5: Sistema de Controle da Manutenção
## Arquitetura de Software e Contrato de Integração de APIs

---

### 1. Visão Geral da Arquitetura em Camadas

O sistema adota uma arquitetura em 3 camadas (com desacoplamento de responsabilidades), executado localmente ou em servidor de borda na fábrica:

```
+-------------------------------------------------------------------+
|               CAMADA DE APRESENTAÇÃO (UI / Frontend)             |
|  - Streamlit Web Application (Desktop & Tablet)                   |
|  - Componentes gráficos interativos (Plotly)                      |
|  - Auto-refresh para painel sinótico (5 a 10s)                    |
+-------------------------------------------------------------------+
                                 | (Chamadas Python / DTOs)
+-------------------------------------------------------------------+
|               CAMADA DE NEGÓCIO E SERVIÇOS (Services)             |
|  - AuthService: Validação de credenciais e permissões (RBAC)      |
|  - EquipamentoService: Gestão de máquinas e estados operacionais |
|  - ChamadoService: Ciclo de vida da OS, cronômetro e downtime     |
|  - RelatorioService: Métricas industriais (MTTR, MTBF, Downtime)  |
|  - RestApiServer: Servidor REST local (FastAPI/Flask)             |
+-------------------------------------------------------------------+
                                 | (SQLAlchemy 2.0 / sqlite3)
+-------------------------------------------------------------------+
|            CAMADA DE ACESSO E PERSISTÊNCIA (Data Access)          |
|  - SQLite (Base local `manutencao.db` unificada)                  |
|  - Transações ACID, integridade referencial e Trilha de Auditoria |
+-------------------------------------------------------------------+
```

---

### 2. Estrutura de Pastas Padronizada

```text
management-control/
├── app.py                      # Ponto de entrada Streamlit (Roteador de perfis e layout)
├── api.py                      # Servidor de API REST (FastAPI/Flask) para integração
├── requirements.txt            # Dependências (streamlit, plotly, pandas, sqlalchemy, etc.)
├── config.py                   # Configurações de banco, paths e constantes do sistema
├── database.py                 # Conexão, sessão e inicialização do banco SQLite
│
├── pages/                      # Telas da Aplicação Streamlit
│   ├── 01_painel_maquinas.py   # Painel sinótico com cards coloridos (auto-refresh)
│   ├── 02_abrir_chamado.py     # Formulário de abertura rápida de OS
│   ├── 03_fila_chamados.py     # Fila de atendimento técnico (com filtro e "Assumir")
│   ├── 04_ordem_servico.py     # Gestão da OS em andamento (cronômetro, peças, laudo)
│   ├── 05_dashboard.py         # Dashboard de KPIs para o Gestor (MTTR, Downtime, etc.)
│   ├── 06_historico.py         # Consulta detalhada de intervenções com exportação CSV
│   └── 07_cadastros.py         # CRUD de Equipamentos, Peças e Usuários
│
├── services/                   # Camada de Regras de Negócio Puras
│   ├── auth_service.py         # Autenticação e sessão
│   ├── equipamento_service.py  # Consulta e transição de status das máquinas
│   ├── chamado_service.py      # Abertura, atendimento, conclusão e cálculo de downtime
│   └── relatorio_service.py    # Cálculo de MTTR, MTBF, disponibilidade e séries temporais
│
├── models/                     # Modelos ORM / Esquema de Dados
│   ├── entities.py             # Modelos Usuario, Equipamento, Chamado, Peca, etc.
│   └── schemas.py              # Pydantic Schemas para entrada e saída de dados
│
├── db/                         # Arquivos de banco e migrações
│   ├── schema.sql              # Script DDL com dados seed
│   └── manutencao.db           # Banco de dados SQLite persistido
│
└── docs/                       # Documentação SDD e Manuais
    ├── 01_SDD_SPECIFICATION.md
    ├── 02_DATABASE_SCHEMA.sql
    ├── 03_ARCHITECTURE_AND_API.md
    ├── 04_UI_UX_DESIGN_SYSTEM.md
    └── 05_VIBE_CODING_MASTER_PROMPT.md
```

---

### 3. Contrato de Integração com Outros Grupos (Mini-ERP AMATECH)

O módulo de Manutenção disponibiliza uma API REST JSON local (porta padrão `5002` ou unificada) para fornecer dados à equipe de **Visualização Geral (Letícia/Radier)** e cruzar dados com **Qualidade (Anderson)** e **Rastreabilidade (Waddi)**.

#### Endpoint 1: Healthcheck e Status do Sistema
* **Método:** `GET`
* **Rota:** `/api/status`
* **Resposta Esperada:**
```json
{
  "sistema": "Controle da Manutencao",
  "status": "online",
  "versao": "1.0.0",
  "responsavel": "Equipe Orlando"
}
```

#### Endpoint 2: Consulta de Máquinas e Status em Tempo Real
* **Método:** `GET`
* **Rota:** `/api/equipamentos`
* **Resposta Esperada:**
```json
[
  {
    "id": 1,
    "codigo_tag": "SMT-01",
    "nome": "Insersora Automática High-Speed",
    "setor": "SMT",
    "posto_trabalho": "Posto 01",
    "status_operacional": "OPERACIONAL"
  },
  {
    "id": 2,
    "codigo_tag": "SMT-02",
    "nome": "Forno de Refusão 10 Zonas",
    "setor": "SMT",
    "posto_trabalho": "Posto 02",
    "status_operacional": "EM_MANUTENCAO"
  },
  {
    "id": 4,
    "codigo_tag": "TEST-01",
    "nome": "Testador ICT (In-Circuit Test)",
    "setor": "Testes Funcionais",
    "posto_trabalho": "Posto 01",
    "status_operacional": "PARADA"
  }
]
```

#### Endpoint 3: Consulta de Ocorrências e Histórico de Chamados
* **Método:** `GET`
* **Rota:** `/api/manutencao/chamados`
* **Resposta Esperada:**
```json
[
  {
    "id_chamado": 1,
    "equipamento_tag": "SMT-01",
    "equipamento_nome": "Insersora Automática High-Speed",
    "setor": "SMT",
    "operador": "Carlos Mendonça",
    "tecnico": "João Lima Silva",
    "prioridade": "ALTA",
    "tipo_manutencao": "CORRETIVA",
    "status_chamado": "CONCLUIDO",
    "descricao_falha": "Travamento no feeder de alimentação de resistores.",
    "diagnostico_tecnico": "Correia do alimentador ressecada com desgaste excessivo.",
    "causa_raiz": "Desgaste mecânico / Fadiga de componente",
    "data_hora_abertura": "2026-10-25T14:00:00",
    "data_hora_inicio": "2026-10-25T14:15:00",
    "data_hora_fim": "2026-10-25T15:00:00",
    "downtime_minutos": 60,
    "pecas_trocadas": [
      {
        "codigo_peca": "PN-COR-100",
        "nome": "Correia Dentada de Alimentador SMT",
        "quantidade": 1.0,
        "unidade": "UN"
      }
    ]
  }
]
```

#### Endpoint 4: Indicadores Consolidados para o Dashboard Geral
* **Método:** `GET`
* **Rota:** `/api/manutencao/indicadores`
* **Resposta Esperada:**
```json
{
  "downtime_total_minutos": 60,
  "mttr_minutos": 45.0,
  "mtta_resposta_minutos": 15.0,
  "total_chamados": 3,
  "chamados_abertos": 1,
  "chamados_em_andamento": 1,
  "chamados_concluidos": 1,
  "maquinas_operacionais": 6,
  "maquinas_em_manutencao": 1,
  "maquinas_paradas": 1,
  "disponibilidade_geral_pct": 98.75
}
```
