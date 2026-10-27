# AMATECH Smart Factory — Projeto 5: Sistema de Controle da Manutenção
## Documento de Especificação de Software Orientado a Especificação (SDD)

---

### 1. Visão Geral e Contexto Operacional

* **Instituição:** Faculdade Matias Machline (FMM) — Engenharia da Computação
* **Disciplina:** Projeto Integrador — Ambiente Fabril I
* **Professor:** Prof. Dawesley da Costa Mota
* **Empresa / Cenário:** AMATECH Electronics Indústria e Comércio Ltda. (Fabricante de notebooks no Polo Industrial de Manaus - PIM; capacidade nominal: 3.000 notebooks/dia em 2 turnos).
* **Equipe de Desenvolvimento:** Orlando Vandres (Líder / Scrum Master), Breno Silva (Backend e Banco de Dados), Ariadne Araújo (Frontend e UX/Design), Luciano Cavalcante e Leonora Lima (QA, Testes e Dashboard).
* **Projeto:** Projeto 5 — Sistema de Controle da Manutenção (`management-control`).
* **Problema Diagnosticado (Problema 4):** Ausência de histórico de manutenção. Falhas de máquinas comunicadas por bilhetes ou verbalmente, ausência de registro formal de ordens de serviço (OS), falta de mensuração do tempo de parada (*downtime*) e nenhuma rastreabilidade de peças substituídas.

---

### 2. Máquina de Estados e Ciclo de Vida da OS e Equipamento

O sistema opera sincronizando o status do chamado de manutenção com o status operacional da máquina:

| Evento de Transição | Ação do Usuário / Sistema | Status do Chamado | Status do Equipamento | Timestamp Gravado |
| :--- | :--- | :--- | :--- | :--- |
| **Abertura de Chamado** | Operador identifica falha e submete o chamado | `ABERTO` | `PARADA` *(vermelho)* | `data_hora_abertura = now()` |
| **Início de Atendimento** | Técnico assume a OS na fila técnica | `EM_ANDAMENTO` | `EM_MANUTENCAO` *(amarelo)* | `data_hora_inicio_atendimento = now()` |
| **Conclusão de Reparo** | Técnico registra diagnóstico, causa raiz, peças e encerra OS | `CONCLUIDO` | `OPERACIONAL` *(verde)* | `data_hora_fim_atendimento = now()`, calcula `downtime_minutos` |
| **Cancelamento** | Gestor/técnico identifica alarme falso ou chamado indevido | `CANCELADO` | `OPERACIONAL` *(verde)* | Registra em auditoria |

---

### 3. Matriz de Funcionalidades (Técnica MoSCoW)

* **M (Must have — Essencial no MVP):**
  * **F01 (Autenticação e RBAC):** Login por matrícula e senha com controle de acesso por perfil (`OPERADOR`, `TECNICO`, `GESTOR`).
  * **F02 (Painel Sinótico de Máquinas):** Grid com cards coloridos em tempo real (Verde/Amarelo/Vermelho) das máquinas das linhas SMT e Teste, com atualização automática (auto-refresh a cada 5–10s).
  * **F03 (Abertura Rápida de Chamado):** Seleção de máquina (com preenchimento automático de setor e posto), nível de prioridade (Baixa, Média, Alta, Crítica) e descrição da falha.
  * **F05 (Fila de Chamados Técnicos):** Listagem e ordenação por prioridade e tempo de espera dos chamados com status `ABERTO`.
  * **F06 (Assumir OS):** Ação do técnico para vincular seu usuário à OS, transicionando o status para `EM_ANDAMENTO`.
  * **F07 (Atendimento da OS com Cronômetro):** Interface técnica com exibição de tempo decorrido, formulário de diagnóstico técnico, causa raiz e tipo de manutenção (`CORRETIVA` ou `PREVENTIVA`).
  * **F08 (Registro de Peças Trocadas):** Vinculação de peças e insumos do catálogo com quantidade substituída.
  * **F09 (Conclusão da OS e Cálculo de Downtime):** Fechamento da OS, gravação do carimbo final, cálculo do tempo de parada total e liberação da máquina para `OPERACIONAL`.
  * **F11 (Histórico Filtrável e Exportação):** Consulta detalhada de intervenções com filtros múltiplos e exportação para CSV.
  * **F12 (Dashboard Gerencial de Indicadores):** Exibição de KPIs industriais (Downtime acumulado, MTTR, chamados por status, ranking de falhas por máquina/setor).
  * **F14 (CRUD de Equipamentos):** Cadastro, edição e inativação lógica (`ativo = false`) de equipamentos.
  * **F15 (CRUD de Usuários):** Gestão de operadores, técnicos e gestores.

* **S (Should have — Importante no ciclo):**
  * **F04 (Acompanhamento do Operador):** Visão dos chamados abertos pelo próprio operador.
  * **F10 (Manutenção Preventiva):** Abertura e agendamento de intervenções preventivas programadas.
  * **F16 (CRUD do Catálogo de Peças):** Gestão de peças sobressalentes.
  * **F17 (Trilha de Auditoria - `historico_status`):** Log imutável de todas as alterações de status de máquina.

* **C (Could have — Desejável):**
  * **F13 (Relatório em PDF):** Emissão de relatório formatado para impressão ou auditoria.

---

### 4. Regras de Negócio Críticas (RNs)

* **RN01:** Usuários inativos (`ativo = false`) são bloqueados no login. A navegação do menu é restrita ao perfil do usuário autenticado:
  * *Operador:* Painel de Máquinas, Meus Chamados, Abertura de Chamado.
  * *Técnico:* Painel de Máquinas, Fila de Chamados, Ordem de Serviço em Atendimento, Histórico.
  * *Gestor:* Visão completa (Painel, Fila, Histórico, Dashboard de KPIs, Cadastros).
* **RN02:** **Bloqueio de redundância:** Não é permitido abrir um novo chamado para uma máquina que já esteja com status `PARADA` ou `EM_MANUTENCAO`. O sistema deve exibir a OS ativa existente.
* **RN03:** **Responsabilidade única:** Apenas um técnico pode assumir cada OS. A OS só pode ser concluída pelo técnico responsável ou pelo perfil Gestor.
* **RN04:** **Obrigatoriedade de laudo técnico:** Os campos `diagnostico_tecnico`, `causa_raiz` e `tipo_manutencao` são estritamente obrigatórios para a conclusão da OS.
* **RN05:** **Cálculo de Downtime automatizado e imutável:**
  $$\text{downtime\_minutos} = \frac{\text{data\_hora\_fim\_atendimento} - \text{data\_hora\_abertura}}{60\text{ s}}$$
  O valor deve ser calculado pelo backend no momento da conclusão e nunca digitado manualmente.
* **RN06:** **Integridade de timestamps:** Os carimbos de data/hora são gerados no servidor via `CURRENT_TIMESTAMP`, impedindo adulteração pelo cliente.
* **RN07:** **Soft Delete (Inativação Lógica):** Equipamentos, peças e usuários nunca sofrem exclusão física (`DELETE`) caso possuam vínculos históricos; são marcados como `ativo = false`.
* **RN08:** **Auditoria contínua:** Toda e qualquer alteração de status operacional de um equipamento dispara um registro obrigatório na tabela `historico_status`.
* **RN09:** Quantidade de peças trocadas deve ser estritamente maior que zero ($\text{quantidade} > 0$).

---

### 5. Métricas e Fórmulas de Indicadores Industriais

1. **Downtime Acumulado:**
   $$\text{Downtime Total} = \sum \text{downtime\_minutos dos chamados concluídos no período}$$
2. **MTTR (Mean Time To Repair - Tempo Médio de Reparo):**
   $$\text{MTTR} = \frac{\sum (\text{data\_hora\_fim\_atendimento} - \text{data\_hora\_inicio\_atendimento})}{\text{Número de chamados concluídos}}$$
3. **Tempo Médio de Resposta (MTTA - Mean Time to Acknowledge):**
   $$\text{MTTA} = \frac{\sum (\text{data\_hora\_inicio\_atendimento} - \text{data\_hora\_abertura})}{\text{Número de chamados atendidos}}$$
4. **MTBF (Mean Time Between Failures - Tempo Médio Entre Falhas):**
   $$\text{MTBF} = \frac{\text{Tempo Operacional Total da Máquina}}{\text{Número de Falhas Corretivas}}$$
5. **Disponibilidade Operacional:**
   $$\text{Disponibilidade (\%)} = \left(1 - \frac{\text{Downtime Total}}{\text{Tempo Total Programado}}\right) \times 100$$
