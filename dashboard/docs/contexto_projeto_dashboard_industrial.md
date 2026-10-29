# Contexto do projeto: Dashboard Industrial (AMATECH Smart Factory)

> **Para que serve este arquivo.** Dar a um agente de IA o contexto necessário para ajudar a equipe do Projeto 3 a integrar o Dashboard Industrial com os sistemas das outras equipes da AMATECH Smart Factory.
>
> **Como ler.** Cada informação está marcada com o seu grau de certeza:
> - **[DECIDIDO]**: aprovado pela equipe; não mudar sem consultar a equipe.
> - **[PROPOSTA]**: sugerido, mas ainda não validado pela equipe.
> - **[SIMULADO]**: dado fictício criado para testes e exemplos.
> - **[DESCONHECIDO]**: informação que não estava disponível quando este arquivo foi escrito.
>
> **Situação do arquivo.** Reflete o projeto ao final da etapa OA2. O andamento da OA3 (desenvolvimento) **não está registrado aqui** e deve ser atualizado pela equipe (seção 3.3).

---

## 1. Cenário: a AMATECH e o Projeto Integrador

### 1.1 A empresa (fictícia)

| Item | Valor |
| --- | --- |
| Razão social | AMATECH Electronics Indústria e Comércio Ltda. |
| Local | Polo Industrial de Manaus (AM) |
| Produto | Notebooks (uso pessoal e corporativo) |
| Produção média | 3.000 notebooks por dia |
| Regime | Dois turnos |
| Colaboradores | Cerca de 420 |
| Automação | Parcial: equipamentos modernos em algumas etapas, baixa integração entre recursos físicos e sistemas |

**Fluxo produtivo:** Recebimento de materiais → Armazenamento → Separação de componentes → Linha SMT → Inserção manual → Montagem final → Instalação de software → Testes funcionais → Inspeção da qualidade → Embalagem → Expedição. Produtos reprovados na inspeção voltam a etapas anteriores (retrabalho).

### 1.2 Problemas gerais identificados no diagnóstico da empresa

O programa de transformação digital "AMATECH Smart Factory" partiu destes problemas:

1. Ausência de integração entre setores da fábrica
2. Registros feitos manualmente
3. Dificuldade para acompanhar a produção em tempo real
4. Baixa rastreabilidade dos produtos
5. Demora na identificação de falhas
6. Ausência de indicadores atualizados
7. Pouca utilização de tecnologias digitais
8. Inexistência de sistemas inteligentes de apoio à decisão

### 1.3 Como o projeto funciona

- É um **Projeto Integrador** da disciplina Ambiente Fabril I (Engenharia da Computação, Fundação Matias Machline, 2026).
- Cada equipe da turma representa uma "empresa de tecnologia" contratada pela AMATECH e desenvolve um **MVP** para um problema específico da fábrica.
- **Ao final do semestre, todas as soluções devem compor o ecossistema da AMATECH Smart Factory**, mostrando sistemas diferentes trabalhando de forma integrada. É daí que vem a necessidade deste arquivo.
- Etapas: **OA1** (diagnóstico e requisitos), **OA2** (modelagem da solução), **OA3** (desenvolvimento do MVP). **[DESCONHECIDO]** As etapas posteriores à OA3 e os critérios exatos de integração entre equipes não estão registrados aqui; consultar o enunciado do Projeto Integrador.

### 1.4 Outros projetos da turma

**[DESCONHECIDO]** Este arquivo não traz a lista completa dos outros projetos, nem os nomes das equipes, tecnologias ou modelos de dados deles. O que se sabe:

- O enunciado lista vários projetos e problemas; o Projeto 3 é o nosso.
- Há, segundo a leitura inicial do enunciado, um projeto ligado a **qualidade** (Projeto 4) e um ligado a **manutenção** (Projeto 5). **Confirmar nomes e escopos no enunciado.**
- Os demais sistemas resolvem outros problemas da lista da seção 1.2.

O agente deve **pedir à equipe** a descrição de cada sistema a integrar (o que faz, que dados gera, em que formato e tecnologia) antes de propor qualquer integração.

---

## 2. O nosso projeto

| Item | Valor |
| --- | --- |
| Projeto | Projeto 3: Dashboard Industrial |
| Problema atacado | Problema 8: Indicadores dispersos (produção, qualidade, manutenção e perdas analisados em arquivos separados) |
| Objetivo | Painel único que acompanha a produção com produtividade, defeitos, retrabalho, tempo de parada, perdas e atendimento da meta |
| Equipe | Letícia (líder), Vinicius (analista de processos), Mateus (desenvolvedor), Radier (desenvolvedor de interface), Jose Orlando (testes e documentação) |

**Problema central (OA1):** a AMATECH não tem um painel único e atualizado que consolide, em tempo hábil, os indicadores da linha. Os registros são feitos em papel ou planilha, normalmente no fim do turno, e consolidados manualmente. Desvios do início do turno podem levar horas para serem percebidos.

**Solução (OA2):** um banco de dados único, alimentado por formulários (no momento do evento) e por planilhas CSV, com indicadores calculados na hora da consulta e exibidos em um painel com semáforo (verde, amarelo e vermelho).

**Relação com os problemas gerais (seção 1.2):** o Dashboard ataca principalmente os itens 2, 3, 5 e 6, e é o candidato natural a **painel central** do ecossistema, porque consolida dados de várias áreas.

---

## 3. Andamento

### 3.1 OA1: diagnóstico e requisitos (concluída)

- Diagnóstico do processo, AS-IS e TO-BE, atores, causas e pontos críticos.
- Requisitos RF01 a RF14, RNF01 a RNF06 e regras RN01 a RN05.
- Não houve programação nesta etapa.

### 3.2 OA2: modelagem da solução (concluída)

Entregáveis produzidos e aprovados:

| Entregável | Arquivo(s) |
| --- | --- |
| MER (17 tabelas) | mer_dashboard_industrial.png / .drawio |
| Diagrama de casos de uso (7 atores, 16 casos) | casos_de_uso_dashboard.png / .drawio |
| Diagrama de classes | classes_dashboard.png / .drawio |
| Fluxo do sistema | fluxo_sistema_dashboard.png / .drawio |
| Arquitetura | arquitetura_dashboard.png / .drawio |
| Wireframes (10 telas) | wireframe_T01 a T10 (.png) / wireframes_dashboard.drawio |
| Planejamento da OA3 | planejamento_oa3_gantt.png |
| Script do banco | banco_dashboard_industrial.sql (versão final da OA2, ver seção 5.4) |
| Relatório da OA2 | Documento "Relatório OA2 — Modelagem da Solução" |
| Apresentação | Slides da OA2 (14 slides) |

Pendências registradas ao fim da OA2:

- [x] Atualizar o script SQL (seção 5.4)
- [ ] Preencher o nome do professor no relatório e exportar em PDF

### 3.3 OA3: desenvolvimento (planejada; andamento a atualizar)

**[DECIDIDO]** Cronograma em cinco sprints semanais:

| Sprint | Período | Foco | Entregas |
| --- | --- | --- | --- |
| S1 | 01/10 a 07/10/2026 | Base | GitHub com a estrutura de pastas, banco, classes de dados, Repositorio, Trello |
| S2 | 08/10 a 14/10 | Acesso e cadastros | Login (T01), menu por perfil, Usuários (T10), Cadastros (T09) |
| S3 | 15/10 a 21/10 | Registros | ServicoRegistro; telas T03 a T06; modelos de planilha CSV |
| S4 | 22/10 a 28/10 | Painel e importação | CalculadoraIndicadores, AvaliadorAlertas; Painel (T02), Histórico (T08), Importação (T07) |
| S5 | 29/10 a 04/11 | Testes e entrega | Testes, correções, README, manual de instalação, vídeo |

**[DESCONHECIDO]** O que já foi implementado. **A equipe deve preencher abaixo antes de usar este arquivo:**

- Sprint atual: ______
- Já implementado e funcionando: ______
- Desvios em relação ao planejado: ______
- Formato final dos modelos de planilha CSV (previsto para a S3): ______

---

## 4. Solução técnica

### 4.1 Arquitetura [DECIDIDO]

Quatro camadas; **cada camada só conversa com a camada logo abaixo**.

| Camada | Pasta | Tecnologia | Responsabilidade |
| --- | --- | --- | --- |
| 1. Apresentação | `app.py`, `pages/` | Streamlit, Plotly | Telas; não calcula nem acessa o banco |
| 2. Serviços | `servicos/` | Python, pandas, hashlib | Regras de negócio e **fórmulas dos indicadores** |
| 3. Acesso a dados | `acesso_dados/` | sqlite3 | Única parte que escreve SQL (classe Repositorio) |
| 4. Dados | `database/` | SQLite (arquivo `banco.db`) | 17 tabelas; restrições de integridade |
| Transversal | `modelos/` | Python | 13 classes de dados usadas pelas camadas 1 a 3 |

- Linguagem única: Python 3.11 ou superior.
- Execução: um computador roda `streamlit run app.py`; os demais da rede acessam pelo navegador.
- Todas as ferramentas são gratuitas (RNF06).
- **Os indicadores não são gravados no banco**: são calculados na consulta pela CalculadoraIndicadores.

### 4.2 Classes de serviço [DECIDIDO]

| Classe | Responsabilidade |
| --- | --- |
| ServicoAutenticacao | Login, hash de senha, permissões por perfil |
| ServicoRegistro | Valida (RN01 a RN09) e grava produção, defeito, retrabalho, parada (incluindo `encerrar_parada`) e perda |
| ImportadorCSV | Lê e valida planilhas; usa o ServicoRegistro; grava tudo ou nada (RN06) |
| CalculadoraIndicadores | Calcula os seis indicadores para um período (recebe um Filtro) |
| AvaliadorAlertas | Define a cor do semáforo a partir da tabela `parametro_alerta` |
| Filtro | Data inicial, data final, turno e produto |
| Repositorio | Consultas, gravações e transações no SQLite |

### 4.3 Perfis de acesso [DECIDIDO]

Permissões fixas no código (não há tabela de permissões).

| Perfil | Pode |
| --- | --- |
| Operador de estação | Registrar produção e defeitos |
| Inspetor de qualidade | Registrar defeitos e retrabalho |
| Manutenção | Registrar paradas |
| Supervisor de produção | Tudo dos três acima + metas, perdas, importação de CSV, painel, histórico e ajuste dos limites do semáforo |
| Gestor/Diretoria | Painel e histórico (somente leitura) |
| Administrador | Usuários, perfis e cadastros básicos |

### 4.4 Telas [DECIDIDO]

T01 Login · T02 Painel · T03 Produção e metas · T04 Qualidade · T05 Paradas · T06 Perdas · T07 Importação de planilhas · T08 Histórico · T09 Cadastros · T10 Usuários.

---

## 5. Modelo de dados

### 5.1 Tabelas [DECIDIDO]

Todos os relacionamentos são 1:N. PK = chave primária; FK = chave estrangeira.

| Tabela | Campos (FK entre parênteses) | Observações |
| --- | --- | --- |
| turno | id_turno, nome, hora_inicio, hora_fim, duracao_min | duracao_min usada na produtividade |
| produto | id_produto, modelo (único), descricao, ativo | |
| estacao | id_estacao, nome (único), setor, ordem_fluxo | |
| maquina | id_maquina, codigo (único), nome, id_estacao (estacao) | |
| tipo_defeito | id_tipo_defeito, descricao (único), categoria | categoria: funcional, visual ou documental |
| motivo_parada | id_motivo, descricao (único), tipo | tipo: corretiva, preventiva ou operacional |
| tipo_perda | id_tipo_perda, descricao (único) | |
| parametro_alerta | id_parametro, indicador (único), limite_verde, limite_amarelo, sentido | sentido: maior_melhor ou menor_melhor |
| meta_producao | id_meta, data, id_turno (turno), id_produto (produto), qtd_meta, registrado_por (usuario) | UNIQUE (data, id_turno, id_produto) |
| registro_producao | id_producao, data, id_turno (turno), id_produto (produto), qtd_realizada, qtd_aprovada, qtd_reprovada, registrado_por (usuario), registrado_em, id_importacao (importacao, opcional) | qtd_aprovada + qtd_reprovada = qtd_realizada |
| defeito | id_defeito, id_producao (registro_producao), id_tipo_defeito (tipo_defeito), id_estacao (estacao), id_maquina (maquina, opcional), quantidade, data_hora, observacao, registrado_por, id_importacao (opcional) | |
| retrabalho | id_retrabalho, id_defeito (defeito), id_estacao_retorno (estacao), motivo, quantidade, data_hora, registrado_por | |
| parada | id_parada, id_estacao (estacao), id_maquina (maquina, opcional), id_turno (turno), id_motivo (motivo_parada), inicio, fim (opcional), observacao, registrado_por, id_importacao (opcional) | fim vazio = parada em andamento; fim > inicio |
| perda | id_perda, data, id_turno, id_estacao, id_produto, id_tipo_perda (tipo_perda), quantidade, observacao, registrado_por, id_importacao (opcional) | quantidade > 0 |
| perfil | id_perfil, nome (único), descricao | |
| usuario | id_usuario, nome, login (único), senha_hash, id_perfil (perfil), ativo, criado_em | usuários são desativados, nunca apagados |
| importacao | id_importacao, nome_arquivo, tipo_dado, data_hora, id_usuario (usuario), linhas_lidas, linhas_importadas, linhas_rejeitadas, status | tipo_dado: producao, defeito, parada ou perda; status: concluida ou rejeitada |

Datas no formato `AAAA-MM-DD`; data e hora no formato `AAAA-MM-DD HH:MM`.

### 5.2 Decisões de modelagem importantes para integração [DECIDIDO]

1. **A produção é registrada por data, turno e produto, sem estação.** O mesmo notebook passa por todas as estações; registrar por estação contaria várias vezes. A estação aparece em defeito, parada e perda.
2. **Os dados de produção são agregados (quantidades por turno), não por unidade.** Não existe número de série de notebook no modelo. Uma integração com um sistema de rastreabilidade por unidade exigiria uma decisão nova da equipe.
3. **A soma dos defeitos não precisa ser igual aos reprovados**, porque um notebook pode ter mais de um defeito.
4. **Todo defeito pertence a um registro de produção** (id_producao). Um dado de defeito vindo de outro sistema precisa ser associado a uma combinação de data, turno e produto já registrada.
5. **A duração da parada é calculada** a partir de início e fim, nunca digitada.
6. **Todo evento guarda a origem**: `registrado_por` (quem lançou) e `id_importacao` (de qual planilha veio; vazio = formulário).

### 5.3 Regras de negócio [DECIDIDO]

| Regra | Descrição |
| --- | --- |
| RN01 | Todo registro de produção tem data, turno e produto |
| RN02 | Retrabalho exige estação de retorno e motivo |
| RN03 | Atendimento à meta só é calculado se houver meta cadastrada |
| RN04 | Toda parada tem motivo |
| RN05 | Indicadores são calculados por período, nunca acumulados indefinidamente |
| RN06 | Importação com qualquer linha inválida não grava nada; o sistema lista linha, coluna e problema |
| RN07 | Toda perda tem tipo e quantidade maior que zero |
| RN08 | Limites do semáforo são configuráveis pelo Supervisor, sem mexer no código |
| RN09 | No máximo uma meta por data, turno e produto |
| RNF04 | Integridade: aprovados + reprovados = realizada; fim da parada depois do início |
| RNF07 | Senhas guardadas só como hash; cada perfil acessa apenas suas funções |

### 5.4 Script SQL

O arquivo `database/banco_dashboard_industrial.sql` está na **versão final da OA2** e foi testado no SQLite: cria as 17 tabelas, as restrições e os dados de teste, e recusa os dados inválidos testados (7 de 7). Ajustes feitos em relação à primeira versão:

| Antes | Versão final |
| --- | --- |
| Tinha 5 views de indicadores | Sem views: as fórmulas ficam em Python (CalculadoraIndicadores) |
| Limite amarelo da meta = 85 | Limite amarelo da meta = 75 (vermelho abaixo de 75%) |
| Perfil Supervisor sem os limites | Supervisor também ajusta os limites do semáforo |

**[SIMULADO]** O script cria um usuário de teste `admin` com senha `admin123` (hash SHA-256 simples, só para testes). A versão definitiva deve usar a função de senha com "sal" do hashlib e trocar essa senha.

---

## 6. Indicadores [DECIDIDO]

| Indicador | Fórmula | Unidade | Semáforo |
| --- | --- | --- | --- |
| Atendimento da meta | produção realizada ÷ meta do turno × 100 | % | Verde ≥ 95; amarelo ≥ 75; vermelho < 75 |
| Produtividade | produção realizada ÷ (duração do turno − tempo de parada), em horas | unid/h | Sem cor |
| Índice de defeitos | reprovados ÷ produção realizada × 100 | % | Verde ≤ 2; amarelo ≤ 5; vermelho > 5 |
| Índice de retrabalho | quantidade em retrabalho ÷ produção realizada × 100 | % | Verde ≤ 2; amarelo ≤ 5; vermelho > 5 |
| Tempo de parada | soma das durações das paradas do período | min | Sem cor |
| Perdas | soma das quantidades perdidas do período, por tipo | unid | Sem cor |

Os limites são **proposta da equipe**, guardados na tabela `parametro_alerta`.

**Exemplo de referência** (dados do enunciado, usados em testes e wireframes): 1º turno, Notebook modelo A, meta 1.500, produção 1.420, aprovados 1.360, reprovados 60, parada de 85 min no Testador 02. Resultados: 94,7% da meta, 4,2% de defeitos, 215,7 unid/h. **[SIMULADO]** Turno de 480 min, retrabalho de 30 unidades e perda de 8 unidades.

---

## 7. Integração com outros sistemas

### 7.1 O que já existe como ponto de entrada [DECIDIDO]

**Importação de planilhas CSV (RF16, tela T07, classe ImportadorCSV).**

- Quatro tipos de dado: produção, defeito, parada e perda.
- Cada tipo tem um modelo de planilha baixável na própria tela.
- Fluxo: escolher o tipo → enviar o arquivo → prévia → importar.
- **Tudo ou nada (RN06):** uma linha inválida recusa o arquivo inteiro; o sistema lista linha, coluna e problema.
- Cada importação fica registrada na tabela `importacao`, e cada registro importado guarda o `id_importacao`.
- Somente o perfil Supervisor importa.

**Esse é hoje o único canal de entrada de dados externos previsto no projeto.**

### 7.2 O que já existe como saída [DECIDIDO]

- As tabelas da tela Histórico (T08) podem ser baixadas em CSV (recurso nativo do Streamlit).
- Os indicadores são calculados sob demanda pela CalculadoraIndicadores para qualquer período, turno e produto.

### 7.3 Formato das planilhas CSV [PROPOSTA]

O formato final seria definido na S3 (verificar seção 3.3). Proposta coerente com o modelo de dados, usando **nomes e códigos** em vez de ids internos, para que outros sistemas consigam gerar os arquivos:

| Tipo | Colunas |
| --- | --- |
| producao | data, turno, produto, qtd_realizada, qtd_aprovada, qtd_reprovada |
| defeito | data, turno, produto, tipo_defeito, estacao, maquina_codigo (opcional), quantidade, data_hora, observacao (opcional) |
| parada | estacao, maquina_codigo (opcional), turno, motivo, inicio, fim (opcional), observacao (opcional) |
| perda | data, turno, estacao, produto, tipo_perda, quantidade, observacao (opcional) |

Pontos a definir: codificação (sugestão: UTF-8), separador (sugestão: ponto e vírgula, padrão do Excel em português) e como o defeito encontra o seu registro de produção (sugestão: pela combinação data + turno + produto, que precisa já existir).

### 7.4 Pré-requisito para qualquer integração: cadastros comuns

Para os dados de outros sistemas serem aceitos, **os nomes e códigos precisam bater com os cadastros do Dashboard**. Hoje os cadastros de teste são **[SIMULADO]**:

| Cadastro | Valores de teste |
| --- | --- |
| Turnos | 1º turno (06:00–14:00), 2º turno (14:00–22:00) |
| Produtos | Notebook modelo A, Notebook modelo B |
| Estações | Linha SMT, Inserção manual, Montagem final, Instalação de software, Teste funcional, Inspeção da qualidade, Embalagem |
| Máquinas | TST-02 (Testador 02, estação Teste funcional) |
| Tipos de defeito | Falha no teclado, Falha no touchpad, Tela com defeito, Etiqueta incorreta |
| Motivos de parada | Falha de equipamento (corretiva), Manutenção programada (preventiva), Falta de material (operacional) |
| Tipos de perda | Componente danificado, Material descartado, Embalagem danificada |

Recomendação ao agente: propor às equipes **uma lista única de cadastros** (estações, turnos, produtos, máquinas e tipos), compartilhada por todos os sistemas do ecossistema, antes de trocar qualquer dado.

### 7.5 Possíveis correspondências com outros sistemas [PROPOSTA, a confirmar com cada equipe]

| Se o outro sistema trata de... | Dados que poderia enviar ao Dashboard | Tabela de destino |
| --- | --- | --- |
| Qualidade / inspeção | Reprovações, defeitos por tipo e estação, retrabalho | defeito, retrabalho (e qtd_reprovada) |
| Manutenção | Paradas com motivo, início e fim | parada |
| Apontamento digital da produção | Quantidades produzidas por turno e produto | registro_producao |
| Estoque / materiais | Perdas de componentes e materiais | perda |
| Rastreabilidade por unidade | Dados por número de série | **Não existe destino**: o modelo é agregado (seção 5.2) |

E o caminho inverso: o Dashboard pode fornecer indicadores consolidados a sistemas de apoio à decisão.

### 7.6 Formas de integração possíveis

| Forma | Situação | Observação |
| --- | --- | --- |
| Troca de arquivos CSV | **Prevista** (RF16) | Mais simples; já desenhada no sistema |
| Leitura direta do `banco.db` por outro sistema | Não decidida | Exigiria acordo sobre acesso somente leitura |
| API (serviço web) | Não prevista | Fora do escopo atual do MVP; exigiria nova camada |
| Integração com equipamentos reais | Não exigida | O MVP acadêmico usa dados simulados (OA1, ponto crítico PC03) |

---

## 8. Restrições que o agente deve respeitar

1. **Não alterar decisões marcadas [DECIDIDO]** sem propor à equipe e explicar o impacto.
2. **Toda mudança no modelo de dados** deve refletir-se no MER, no script SQL, no dicionário de dados e na matriz de rastreabilidade.
3. **Manter a arquitetura em camadas**: integração entra pela camada 2 (por exemplo, pelo ImportadorCSV) e nunca grava direto no banco sem passar pelas regras.
4. **Ferramentas gratuitas** e stack em Python (Streamlit + SQLite).
5. **Escopo de MVP acadêmico**: preferir soluções simples e funcionais; prazo da OA3 é 04/11/2026.
6. **Validação "tudo ou nada"** vale para qualquer dado externo (RN06).
7. Responder em **português** e explicar as decisões de forma detalhada para a equipe.

## 9. Perguntas em aberto para o agente levantar

- Quais sistemas serão integrados, de quais equipes, e que dados cada um gera?
- Qual a tecnologia e o formato de saída de cada sistema?
- As equipes aceitam uma lista única de cadastros (estações, turnos, produtos, máquinas, tipos)?
- O formato CSV da seção 7.3 já foi definido na S3? Se sim, qual é?
- Haverá uma demonstração integrada no fim do semestre? Com quais requisitos?
- O Dashboard será o painel central do ecossistema?

## 10. Glossário

| Termo | Significado |
| --- | --- |
| OA1, OA2, OA3 | Etapas avaliativas do Projeto Integrador |
| MVP | Produto mínimo viável: protótipo funcional |
| AS-IS / TO-BE | Processo atual / processo proposto |
| RF, RNF, RN | Requisito funcional, requisito não funcional, regra de negócio |
| UC | Caso de uso |
| T01 a T10 | Telas do sistema (wireframes) |
| Semáforo | Cor de um indicador conforme os limites: verde, amarelo ou vermelho |
| Sprint | Ciclo de desenvolvimento de uma semana |
| Problema 8 | Indicadores dispersos: o problema atacado por este projeto |
