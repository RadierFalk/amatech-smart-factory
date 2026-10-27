# AMATECH Smart Factory — Integração do Ecossistema Mini-ERP
## Mapeamento de Interoperabilidade entre os Projetos da Turma

---

### 1. Visão Geral dos Projetos Clonados em `c:\Users\aluno\projects`

| Projeto | Equipe / Liderança | Stack Técnica | Porta Padrão | Papel no Mini-ERP AMATECH |
| :--- | :--- | :--- | :--- | :--- |
| **`amatech-rastreabilidade`** | Waddington (`waddi`) | Python + FastAPI + SQLite (HTML/JS puro) | `8000` | **Projeto 2 (Problema 5):** Rastreabilidade de notebooks por número de série, lista de componentes (BOM), fluxo de materiais e solicitações/baixas. |
| **`SistemaControleQualidadeDefeitos`** | Anderson Lima | Python + Streamlit + Flask API + SQLite | `5000` (API) / `8501` (UI) | **Projeto 4 (Problema 3):** Registro de defeitos/inspeção de qualidade por posto e máquina, classificação (Maior/Menor/Crítico) e ocorrências. |
| **`management-control`** *(Este projeto)* | Orlando Vandres | Python + Streamlit + FastAPI/Flask + SQLite | `5002` (API) / `8502` (UI) | **Projeto 5 (Problema 4):** Controle de Manutenção, fila de OS, cálculo de *downtime*, medição de MTTR/MTBF e rastreabilidade de peças trocadas. |
| *Central de Visualização* | Letícia & Radier | A definir / Dashboard geral | Consumidor | Módulo de consolidação que consome as APIs dos 3 projetos acima. |

---

### 2. Padrão Arquitetural Observado nos Projetos Vizinhos

1. **Início Simultâneo de UI e API (Padrão Anderson - `SistemaControleQualidadeDefeitos`):**
   * O projeto de Qualidade utiliza uma estratégia elegante no `app.py`:
     ```python
     # Inicia a API Flask em uma thread paralela ao carregar o Streamlit
     if "api_iniciada" not in st.session_state:
         threading.Thread(target=iniciar_api, daemon=True).start()
         st.session_state["api_iniciada"] = True
     ```
   * Isso permite que um único comando (`streamlit run app.py`) suba tanto a interface do usuário quanto os endpoints de integração para os colegas.

2. **Contrato de API com Tags de Máquinas e Eventos (Padrão Waddi - `amatech-rastreabilidade`):**
   * O projeto de Rastreabilidade identifica os postos e máquinas através de tags (`SMT-01`, `SMT-02`, `TEST-01`, `TEST-02`, etc.) e números de série (`AMT-000001` a `AMT-000031`).
   * A rota `/api/v1/eventos` notifica não-conformidades e alterações de etapa.

---

### 3. Como o `management-control` se Conecta a Ambos

1. **Cruzamento de Máquinas (Qualidade ↔ Manutenção):**
   * Quando uma ocorrência crítica é detectada na Qualidade (`TEST-01`), o operador ou sistema de manutenção pode abrir uma OS diretamente para a mesma tag `TEST-01`.
   * A máquina passa para `PARADA` no `management-control`, alertando a linha de produção.

2. **Consumo e Fornecimento de Dados para o Dashboard da Letícia/Radier:**
   * O endpoint `GET http://localhost:5002/api/manutencao/indicadores` entrega:
     ```json
     {
       "sistema": "Controle da Manutencao",
       "downtime_total_minutos": 60,
       "mttr_minutos": 45.0,
       "mtta_resposta_minutos": 15.0,
       "maquinas_paradas": 1,
       "maquinas_em_manutencao": 1,
       "maquinas_operacionais": 6,
       "disponibilidade_geral_pct": 98.75
     }
     ```
