# AMATECH Smart Factory — Sistema de Controle da Manutenção (`management-control`)
**Projeto 5 — Projeto Integrador: Ambiente Fabril I**  
**Faculdade Matias Machline (FMM) | Manaus - AM**

---

## 🏭 Sobre o Projeto

O **Sistema de Controle da Manutenção** (`management-control`) é a solução computacional desenvolvida para a **AMATECH Electronics Indústria e Comércio Ltda.** (fabricante de notebooks no Polo Industrial de Manaus) para solucionar o **Problema 4 — Ausência de Histórico de Manutenção**:
* Eliminação de acionamentos verbais e bilhetes de manutenção;
* Registro formal e digital de Ordens de Serviço (OS);
* Cálculo automatizado e auditoria do tempo de parada de máquinas (*downtime*);
* Rastreabilidade completa de peças e insumos trocados;
* Geração de indicadores de manutenção de classe mundial (**MTTR, MTBF, MTTA e Disponibilidade**);
* Integração direta com os outros módulos do Mini-ERP da AMATECH (Controle de Qualidade, Rastreabilidade e Central de Visualização).

---

## 👥 Equipe de Desenvolvimento
* **Orlando Vandres Lima dos Santos:** Líder / Scrum Master & Integração
* **Breno Silva dos Santos:** Backend, Regras de Negócio & Banco de Dados
* **Ariadne Araujo Farias:** Frontend Streamlit, Wireframes & UX Design
* **Luciano Cavalcante dos Santos & Leonora de Souza Lima:** Testes, Validação & Dashboard de Indicadores
* **Orientação:** Prof. Dawesley da Costa Mota

---

## 📁 Estrutura de Documentação Orientada por Especificação (SDD)

Todas as definições técnicas, arquiteturais e regras de negócio estão formalizadas na pasta `docs/`:

1. [`docs/01_SDD_SPECIFICATION.md`](docs/01_SDD_SPECIFICATION.md): Especificação funcional detalhada (F01–F17), regras de negócio (RN01–RN09), máquina de estados e fórmulas matemáticas dos indicadores.
2. [`docs/02_DATABASE_SCHEMA.sql`](docs/02_DATABASE_SCHEMA.sql): Script DDL e carga de dados de demonstração (seed) compatível com SQLite e PostgreSQL.
3. [`docs/03_ARCHITECTURE_AND_API.md`](docs/03_ARCHITECTURE_AND_API.md): Arquitetura em 3 camadas e contrato oficial de API REST JSON para integração no Mini-ERP.
4. [`docs/04_UI_UX_DESIGN_SYSTEM.md`](docs/04_UI_UX_DESIGN_SYSTEM.md): Design system da AMATECH (cores, cards industriais, padrões de tela e usabilidade para tablets).
5. [`docs/05_VIBE_CODING_MASTER_PROMPT.md`](docs/05_VIBE_CODING_MASTER_PROMPT.md): **Prompt Mestre para Vibe Coding**, pronto para geração do código-fonte completo via IA.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
* Python 3.10 ou superior instalado
* Bibliotecas necessárias:
  ```bash
  pip install streamlit plotly pandas fastapi uvicorn requests
  ```

### 1. Inicializar o Banco de Dados SQLite
```bash
python -c "import sqlite3; conn = sqlite3.connect('manutencao.db'); conn.executescript(open('docs/02_DATABASE_SCHEMA.sql', encoding='utf-8').read()); print('Banco inicializado!')"
```

### 2. Iniciar a Aplicação Web (Streamlit)
```bash
streamlit run app.py
```

### 3. Iniciar o Servidor de API de Integração (Opcional para rede local)
```bash
uvicorn api:app --reload --port 5002
```
