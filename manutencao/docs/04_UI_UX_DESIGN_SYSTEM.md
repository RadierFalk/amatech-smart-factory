# AMATECH Smart Factory — Projeto 5: Sistema de Controle da Manutenção
## Especificação de Interface, Design System e Telas (UI/UX)

---

### 1. Identidade Visual Padronizada (Padrão AMATECH)

Para atender à exigência do professor de que os módulos do Mini-ERP pareçam um software único, o `management-control` utiliza a paleta corporativa oficial da **AMATECH Electronics**:

* **Azul Institucional Primário:** `#1F3A5F` (Cabeçalho, Navbar, Barra Lateral)
* **Azul Secundário de Destaque:** `#2E75B6` (Botões de ação primária, abas ativas, links)
* **Cinza de Fundo:** `#F4F6F9` (Background limpo industrial)
* **Texto Principal:** `#2C3E50` e `#333333`
* **Cores Semânticas de Estado Operacional (RNF04):**
  * **OPERACIONAL:** `#2E9E4F` (Verde escuro / Positivo)
  * **EM_MANUTENCAO:** `#F2B705` (Amarelo âmbar / Atenção)
  * **PARADA:** `#D32F2F` (Vermelho industrial / Alerta crítico)
* **Cores de Prioridade de Chamados:**
  * **BAIXA:** `#6C757D` (Cinza neutro)
  * **MEDIA:** `#0288D1` (Azul informativo)
  * **ALTA:** `#F57C00` (Laranja)
  * **CRITICA:** `#C62828` (Vermelho pulsante)

---

### 2. Estrutura e Especificação das 8 Telas

#### Tela 1: Login e Autenticação (F01)
* **Público:** Todos os colaboradores (Operador, Técnico, Gestor).
* **Campos:** Matrícula (ex: `OP-10234`, `TEC-2001`, `GES-0001`) e Senha.
* **Comportamento:** Valida credenciais no banco SQLite. Após sucesso, carrega a sessão com perfil e redireciona automaticamente para a tela inicial correspondente.

#### Tela 2: Painel Sinótico de Máquinas (F02, RF06)
* **Público:** Operadores, Supervisores e Gestores.
* **Componentes:**
  * Filtro rápido por Setor (`Todos`, `SMT`, `Testes Funcionais`, `Montagem Final`, `Embalagem`).
  * Indicadores rápidos no topo: Total de Máquinas, Operacionais, Em Manutenção, Paradas.
  * Grid de Cards com layout responsivo:
    * Tag da Máquina (`SMT-01`), Nome do Equipamento e Posto.
    * Badge grande de Status com cor semântica (Verde/Amarelo/Vermelho).
    * Se em parada ou manutenção: exibe número da OS ativa e tempo decorrido.
    * Botão de ação rápida: **"Abrir Chamado"** (desabilitado se a máquina já estiver parada, com aviso da OS existente).
  * Atualização automática periódica (auto-refresh a cada 5–10 segundos).

#### Tela 3: Abertura Rápida de Chamado (F03, UC03)
* **Público:** Operador de Produção.
* **Componentes:**
  * Seleção do Equipamento (ao selecionar, setor e posto são pré-preenchidos e bloqueados).
  * Seleção de Prioridade em botões visuais destacados: `[Baixa]`, `[Média]`, `[Alta]`, `[Crítica]`.
  * Tipo de Manutenção: padrão `CORRETIVA` (com opção `PREVENTIVA`).
  * Campo de texto detalhado: "Descrição do Sintoma / Falha Observada".
  * Alerta visual informando que o timestamp de abertura e status `PARADA` serão acionados imediatamente após o clique.
  * Botões: `Confirmar Abertura de OS` e `Cancelar`.

#### Tela 4: Fila de Chamados Técnicos (F05, F06)
* **Público:** Técnicos de Manutenção.
* **Componentes:**
  * Indicadores no topo: Chamados Pendentes, Em Andamento, Concluídos Hoje.
  * Tabela interativa classificada por Prioridade (Crítica no topo) e tempo de espera.
  * Colunas: `Nº OS`, `Tag/Máquina`, `Setor`, `Prioridade`, `Data/Hora Abertura`, `Tempo Parado`, `Operador Solicitante`, `Ação`.
  * Botão de ação em cada linha: **"Assumir OS"** (atribui o técnico logado, marca início do reparo e muda a máquina para `EM_MANUTENCAO`).

#### Tela 5: Ordem de Serviço em Atendimento (F07, F08, F09)
* **Público:** Técnico Responsável pela OS.
* **Componentes:**
  * Cabeçalho da OS: Número, Máquina, Solicitante, Horário de Abertura.
  * **Cronômetro de Reparo em Tempo Real:** tempo corrido desde `data_hora_inicio_atendimento`.
  * Formulário de Laudo Técnico:
    * `Diagnóstico Técnico` (descrição detalhada do problema encontrado).
    * `Causa Raiz` (campo padronizado: ex. Desgaste Mecânico, Falha Elétrica, Erro de Parâmetro, Lubrificação, Fadiga Térmica).
  * Seção de Peças Substituídas:
    * Dropdown para pesquisar no catálogo de peças cadastradas.
    * Campo numérico de quantidade.
    * Botão `Adicionar Peça` e tabela com as peças incluídas nesta OS (com opção de remover).
  * Ações Finais:
    * Botão `Concluir Ordem de Serviço` (calcula downtime total, atualiza status para `CONCLUIDO`, libera máquina para `OPERACIONAL`).

#### Tela 6: Dashboard Gerencial de KPIs (F12, RF10)
* **Público:** Gestor de Manutenção / Gerência Fabril.
* **Componentes:**
  * Filtro de Período (Hoje, Últimos 7 dias, Mês Atual) e Setor.
  * **Cards de Métricas Principais (KPIs):**
    * *Downtime Total Acumulado (minutos / horas)*
    * *MTTR (Tempo Médio de Reparo)*
    * *MTTA (Tempo Médio de Atendimento)*
    * *Disponibilidade Geral (%)*
  * **Gráficos Interativos (Plotly):**
    * Gráfico de Barras: *Downtime Acumulado por Máquina (Ranking de Gargalos)*.
    * Gráfico de Pizza / Rosca: *Distribuição de Chamados por Causa Raiz*.
    * Gráfico de Linhas: *Evolução Diária de Paradas de Linha*.
    * Gráfico de Barras Empilhadas: *Chamados por Setor (SMT vs Testes vs Montagem)*.

#### Tela 7: Histórico de Intervenções e Auditoria (F11, F17)
* **Público:** Gestor e Técnico.
* **Componentes:**
  * Painel de filtros avançados: Máquina, Técnico, Tipo de Manutenção, Status, Intervalo de Datas.
  * Tabela consolidada com paginação e busca textual.
  * Botão de exportação instantânea: **"Exportar Histórico para CSV"**.
  * Visualização da trilha de auditoria (`historico_status`).

#### Tela 8: Cadastros do Sistema (F14, F15, F16)
* **Público:** Gestor de Manutenção.
* **Componentes:**
  * Abas organizadas: `Equipamentos`, `Peças Sobressalentes`, `Usuários`.
  * Formulário de inserção rápida com validações de unicidade (`codigo_tag`, `codigo_peca`, `matricula`).
  * Tabela de registros existentes com botão de ativação/inativação lógica (*Soft Delete*).
