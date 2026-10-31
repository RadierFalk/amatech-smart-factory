# Controle da Qualidade

**AMATECH Smart Factory** · Projeto Integrador *Ambiente Fabril I* · Engenharia da Computação · Fundação Matias Machline · 2026

Setor: **Qualidade (testes e inspeção)** · Projeto 4 → **Problema 3** (controle manual de falhas) · Pasta no repositório único: `qualidade/`

O sistema registra, consulta, pesquisa, filtra, edita e oculta as **ocorrências de defeito** encontradas na produção de notebooks da fábrica fictícia AMATECH Electronics. Mostra indicadores e gráficos da qualidade e **conversa pelas APIs** com os outros três sistemas do ecossistema (Rastreabilidade, Manutenção e Dashboard).

Para usar a tela é preciso **entrar com matrícula e senha**, e o que cada pessoa pode fazer depende do perfil (Administrador, Operador, Almoxarife ou Inspetor de Qualidade). O login vale **só para a tela**: a API e a integração com os outros setores continuam usando as chaves `X-API-Key`.

> Este documento substitui o `README.md` anterior (só da API) e o `README_.md` (documentação da primeira versão, com Flask).
> O resumo do que mudou em todos os setores está em [`../RESUMO_ALTERACOES.md`](../RESUMO_ALTERACOES.md) e o do repositório inteiro, em [`../README.md`](../README.md).

---

## Sumário

1. [Resumo do sistema](#1-resumo-do-sistema)
2. [Lugar no ecossistema](#2-lugar-no-ecossistema)
3. [Estrutura do projeto](#3-estrutura-do-projeto)
4. [Como executar](#4-como-executar)
5. [As telas](#5-as-telas)
6. [Login, perfis e permissões](#6-login-perfis-e-permissões)
7. [Regras das ocorrências](#7-regras-das-ocorrências)
8. [Banco de dados](#8-banco-de-dados)
9. [API da Qualidade](#9-api-da-qualidade)
10. [Integração com os outros setores](#10-integração-com-os-outros-setores)
11. [Variáveis de ambiente](#11-variáveis-de-ambiente)
12. [Servidor da rede (Docker)](#12-servidor-da-rede-docker)
13. [Testes](#13-testes)
14. [Roteiro de demonstração](#14-roteiro-de-demonstração)
15. [Limitações conhecidas](#15-limitações-conhecidas)
16. [O que mudou desde a primeira versão](#16-o-que-mudou-desde-a-primeira-versão)

---

## 1. Resumo do sistema

| Item | Valor |
| --- | --- |
| Tecnologia | Python · Streamlit (telas) · FastAPI (API) · SQLite · Matplotlib · `requests` (integração) |
| Telas | porta **8502** (`/qualidade/` no servidor) |
| API | porta **5000**, processo próprio (`/qualidade/api/...` no servidor) · documentação em `/docs` |
| Banco | `banco/controle_qualidade.db` (versionado no Git) |
| Login | **matrícula + senha** (hash Argon2), 4 perfis; só a tela. A API usa `X-API-Key` e não passa pelo login |
| Dono dos dados | **Ocorrências de defeito**. Os notebooks vêm da Rastreabilidade e as máquinas, da Manutenção |
| Testes | 59, rodam **sem** os outros sistemas no ar |

---

## 2. Lugar no ecossistema

Cada sistema tem o **próprio banco** e só fala com os outros por HTTP. Ninguém lê o banco de ninguém.

```
                 GET  /api/v1/producoes (séries)         ┌──────────────────────┐
Qualidade ─────────────────────────────────────────────► │ Rastreabilidade 8000 │
   │        POST /api/v1/producoes/{serie}/status ─────► └──────────────────────┘
   │
   │        GET  /api/equipamentos (TAGs)                 ┌──────────────────────┐
   ├────────────────────────────────────────────────────► │ Manutenção 5002      │
   │        POST /api/manutencao/chamados ──────────────► └──────────────────────┘
   │
   ▲        GET  /api/ocorrencias?de=&ate=                ┌──────────────────────┐
   └───────────────────────────────────────────────────── │ Dashboard 8501/5003  │
                                                          └──────────────────────┘
```

| Dados | Dono | Papel da Qualidade |
| --- | --- | --- |
| Modelos de notebook e números de série | Rastreabilidade | Consome (cópia local em `produto`) |
| Máquinas (TAGs) | Manutenção | Consome (cópia local em `maquina`) |
| **Ocorrências de defeito** | **Qualidade** | **Dona.** Rastreabilidade, Manutenção e Dashboard usam |
| Chamados de manutenção | Manutenção | Abre chamados pela API deles |
| Estações, turnos, metas e indicadores | Dashboard | — |

---

## 3. Estrutura do projeto

```
qualidade/
├── app.py                     entrada do Streamlit: login, menu por perfil, barra lateral e busca dos cadastros dos setores
├── api.py                     API FastAPI (processo próprio): /api/status e /api/ocorrencias
├── integracao.py              conversa com a Rastreabilidade e a Manutenção
├── banco.py                   todas as consultas SQL (acesso ao SQLite)
├── ocorrencia.py              validação e regras das ocorrências (registrar/editar/ocultar exigem permissão)
├── autenticacao.py            login, hash de senha (Argon2) e gestão de contas
├── permissoes.py              matriz de permissões por perfil (um só lugar)
├── sessao.py                  sessão do usuário: expiração e logout
├── migracao.py                backup + conversão da tabela usuario para o login (repetível)
├── indicadores.py             cálculo dos indicadores do dashboard
├── graficos.py                preparação dos dados dos gráficos
├── criar_banco.py             recria o banco do zero com os dados iniciais
├── simular_dados.py           gera ocorrências aleatórias para demonstração
├── telas/
│   ├── login.py               tela de entrada
│   ├── usuarios.py            gestão de usuários (só Administrador)
│   ├── dashboard.py           indicadores e gráficos
│   ├── registro_ocorrencia.py formulário de registro + opção "Abrir chamado na manutenção"
│   └── historico_ocorrencias.py pesquisa, filtros, edição e ocultação
├── banco/controle_qualidade.db
├── banco/backups/             criada na primeira migração: cópia do banco de antes do login
├── tests/
│   ├── conftest.py            banco temporário no formato antigo, para os testes de login e migração
│   ├── test_api.py            4 testes da API
│   ├── test_integracao.py     6 testes da integração (respostas HTTP simuladas)
│   ├── test_autenticacao.py   25 testes: login, gestão de contas e sessão
│   ├── test_permissoes.py     13 testes: matriz de permissões e autorização nas ocorrências
│   └── test_migracao.py       11 testes: migração do banco e independência da API
├── .streamlit/config.toml     porta da tela: 8502
├── requirements.txt
├── ESTRUTURA_E_INTEGRACAO.md  resumo da estrutura e da integração (OA3)
└── README.md                  este arquivo
```

### Camadas

```
Login (sessao.py ─► autenticacao.py ─► permissoes.py)
  └─► Tela (Streamlit) ─► ocorrencia.py / indicadores.py / graficos.py ─► banco.py ─► SQLite
                                                                        ▲
API (api.py) ───────────────────────────────────────────────────────────┘
integracao.py ─► APIs da Rastreabilidade e da Manutenção
```

A interface não conhece o SQL, e a API também passa por `banco.py`, então o acesso aos dados não é duplicado.

---

## 4. Como executar

### 4.1. No próprio computador (desenvolvimento)

```bash
pip install -r requirements.txt        # inclui argon2-cffi, usado no login

# terminal 1: API (porta 5000)
python -m uvicorn api:app --host 0.0.0.0 --port 5000

# terminal 2: tela (porta 8502)
streamlit run app.py
```

A tela abre em http://localhost:8502 (pede login) e a documentação da API, em http://localhost:5000/docs.

Na **primeira abertura** da tela, o banco é migrado para o login: o sistema cria um backup em `banco/backups/` e converte os usuários antigos nas contas novas (veja a [seção 6](#6-login-perfis-e-permissões)). Acessos seguintes não refazem nada.

Login inicial de teste: matrícula `ADM-0001`, senha `amatech1234` (as quatro contas começam com essa senha).

A tela e a API são **processos separados**: a API continua no ar mesmo que ninguém esteja com a tela aberta. Na raiz do repositório, o `iniciar.ps1` sobe os quatro sistemas de uma vez:

```powershell
powershell -ExecutionPolicy Bypass -File iniciar.ps1
```

Para a integração funcionar, suba também a **Rastreabilidade** (8000) e a **Manutenção** (5002). Se não estiverem no ar, a Qualidade abre normalmente e mostra só um aviso.

### 4.2. No servidor da rede (Docker)

Veja a [seção 12](#12-servidor-da-rede-docker) e o [`../SERVIDOR.md`](../SERVIDOR.md).

---

## 5. As telas

Sem login, só a tela de entrada aparece. Depois de entrar, a barra lateral mostra o **nome, a matrícula e o perfil** de quem está usando, o botão **Sair** e **apenas as páginas permitidas ao perfil**. As páginas são Dashboard, Registrar ocorrência, Histórico e Usuários. A barra lateral também traz o botão **Atualizar cadastros dos setores** e o painel **Integração com os setores**, que mostra quantos notebooks e máquinas foram consultados (ou o aviso de que algum sistema está fora do ar).

### Dashboard
Quatro indicadores:

| Indicador | Como é calculado |
| --- | --- |
| Total de ocorrências | Ocorrências visíveis |
| Ocorrências abertas | Status `Aberta` |
| Produtos reprovados | Números de série **distintos** com situação `Reprovado` |
| Estação com mais ocorrências | Estação com mais registros |

E três gráficos (Matplotlib): ocorrências por **tipo de defeito**, por **estação** e a **tendência por data**.

### Registrar ocorrência
Formulário com produto, data, hora, classificação, situação do produto, status, estação, tipo de defeito, máquina, observação e ação realizada. O **responsável é sempre o usuário logado** (aparece no topo do formulário e não pode ser trocado). A data e a hora já vêm com o momento atual. A caixa **Abrir chamado na manutenção (defeito causado pela máquina)** abre um chamado para a máquina escolhida. Depois de salvar, a tela mostra o que foi enviado a cada setor (ou o aviso, se algum não respondeu).

### Histórico
Tabela das ocorrências visíveis, com:

- **Pesquisa** por ID, produto, tipo de defeito ou estação (um número puro procura o ID);
- **Filtros** combináveis por tipo de defeito, estação, classificação e status;
- **Editar**: carrega a ocorrência no formulário, valida e atualiza, mantendo o mesmo `id_ocorrencia` **e o responsável original**;
- **Ocultar**: a ocorrência **não é apagada**; só passa a `Oculta` e deixa de aparecer nas telas, nos indicadores e na API.

Os botões Editar e Ocultar só aparecem para os perfis que podem usá-los, e cada ocorrência mostra o responsável pelo registro.

### Usuários (somente Administrador)
Lista as contas (matrícula, nome, perfil e situação) e tem o botão **Novo usuário**, que abre uma janela para escolher o **tipo de usuário** e informar nome e senha inicial. Também permite trocar o perfil de outra conta, ativar ou desativar contas e redefinir senhas. Detalhes na [seção 6](#6-login-perfis-e-permissões).

---

## 6. Login, perfis e permissões

### 6.1. Como o login funciona

- Entrada **somente por matrícula e senha**. Não existe escolha de perfil, auto-cadastro nem opção de criar conta na tela de login.
- O sistema confere, nesta ordem: a matrícula existe, a conta está ativa e a senha bate com o hash guardado. O **perfil vem do banco**. Se algo falhar, a tela diz apenas "Matrícula ou senha inválida", sem revelar qual dos dois está errado.
- Senhas ficam **somente como hash Argon2** (`argon2-cffi`). A senha em texto puro não é gravada, não vai para o `st.session_state` e não aparece em log.
- A matrícula aceita maiúsculas ou minúsculas (`adm-0001` = `ADM-0001`). Não há bloqueio por tentativas: errou, aparece o aviso.

### 6.2. Contas iniciais

Os quatro usuários de exemplo do banco antigo **foram convertidos** nas contas do sistema novo. O `id_usuario` não mudou, então cada ocorrência continua ligada à mesma pessoa.

| Matrícula | Nome | Perfil | Era (banco antigo) |
| --- | --- | --- | --- |
| `ADM-0001` | Ana Souza | Administrador | Gestor |
| `OPE-0001` | João Silva | Operador | Operador |
| `ALM-0001` | Carlos Oliveira | Almoxarife | Supervisor de produção |
| `QUA-0001` | Maria Santos | Inspetor de Qualidade | Responsável pela qualidade |

Todas começam com a senha **`amatech1234`** (a variável `QUALIDADE_SENHA_INICIAL` troca o valor). A matrícula identifica o usuário; o perfil define o que ele pode fazer.

> O Carlos era "Supervisor de produção", que só consulta; por isso virou Almoxarife, o perfil de consulta. A Ana era "Gestor" e passou a Administrador, ganhando também a gestão de usuários. Se quiser outro arranjo, troque o perfil na tela **Usuários**.

### 6.3. Perfis e permissões

A matriz fica toda em [`permissoes.py`](permissoes.py). Ajustar o que um perfil pode fazer é mudar uma linha lá, sem mexer nas telas.

| Funcionalidade | Administrador | Operador | Almoxarife | Inspetor de Qualidade |
| --- | :-: | :-: | :-: | :-: |
| Ver Dashboard (indicadores e gráficos) | ✔ | ✔ | ✔ | ✔ |
| Consultar histórico, pesquisar e filtrar | ✔ | ✔ | ✔ | ✔ |
| Atualizar cadastros dos setores | ✔ | ✔ | ✔ | ✔ |
| Registrar ocorrência (responsável = usuário logado) | ✔ | ✔ | ✘ | ✔ |
| Abrir chamado na Manutenção | ✔ | ✔ | ✘ | ✔ |
| Editar ocorrência | ✔ | ✔ | ✘ | ✔ |
| Ocultar ocorrência | ✔ | ✘ | ✘ | ✔ |
| Gerenciar usuários | ✔ | ✘ | ✘ | ✘ |

A autorização **não depende de esconder botões**: `ocorrencia.py` (registrar, editar, ocultar e avisar os setores) e `autenticacao.py` (gestão de contas) conferem a permissão e levantam `PermissaoNegada`. Quem pede a operação é validado de novo no banco a cada chamada, então um perfil ou id forjado no dicionário não vale.

### 6.4. Tela de usuários (Administrador)

- **Novo usuário**: botão que abre uma janela com nome, **tipo de usuário** (os quatro perfis, com a descrição do que cada um faz), senha inicial e confirmação. A **matrícula é gerada pelo tipo** (`ADM-`, `OPE-`, `ALM-` ou `QUA-` e o próximo número) e aparece antes de salvar.
- Trocar o **perfil** de outra conta (a matrícula não muda), **ativar/desativar** contas e **redefinir a senha**.
- Regras: o Administrador não altera o próprio perfil nem desativa a própria conta; o sistema exige sempre pelo menos um Administrador ativo; usuário **nunca é apagado**, só desativado, porque aparece no histórico das ocorrências; senha com no mínimo 8 caracteres; nomes não se repetem.
- Usuários antigos que não são uma das quatro contas iniciais (se existirem) ficam no banco só para o histórico, aparecem como "Sem acesso" e não entram.

### 6.5. Sessão e logout

- O que fica em `st.session_state` é só o id do usuário e o horário do último acesso.
- A cada interação o usuário é lido de novo no banco: **mudar o perfil ou desativar a conta vale na hora**, sem esperar a sessão acabar.
- A sessão **expira após 30 minutos sem uso** (`QUALIDADE_SESSAO_MINUTOS`). O botão **Sair** apaga todo o estado da sessão.
- Limite do Streamlit: a sessão vive na aba. **Atualizar a página (F5) ou abrir outra aba pede login de novo**; as interações normais não pedem.

### 6.6. Migração do banco e backup

A migração (`migracao.py`) roda na abertura da **tela**, uma única vez por processo, e só faz algo se ainda houver o que fazer:

1. Cria o backup em **`banco/backups/controle_qualidade_AAAAMMDD-HHMMSS.db`** (ao lado do banco em uso; no Docker, `/dados/backups/`).
2. Acrescenta à tabela `usuario` as colunas `matricula` (única), `senha_hash`, `ativo`, `data_criacao` e `data_alteracao_senha`.
3. Converte os usuários antigos nas contas da seção 6.2 e define a senha inicial (hash).

Tudo acontece numa transação: ou conclui inteiro ou o banco fica como estava. Rodar de novo não duplica contas nem sobrescreve senhas já alteradas. Nenhuma ocorrência é alterada, e a API **não** executa a migração nem precisa do Argon2.

Para rodar à mão (opcional): `python migracao.py`, dentro de `qualidade/`.

### 6.7. Recuperar o acesso

Se ninguém souber a senha do Administrador, redefina-a direto no banco, com o sistema parado, dentro de `qualidade/`:

```bash
python -c "import banco, autenticacao as a; u = banco.buscar_usuario_por_matricula('ADM-0001'); banco.atualizar_senha_hash(u['id_usuario'], a.gerar_hash('nova-senha-123'))"
```

Se algo der errado na migração, restaure o arquivo de `banco/backups/` por cima de `banco/controle_qualidade.db`.

### 6.8. Login de usuário × chaves entre sistemas

| | Login de usuário | Chaves de API |
| --- | --- | --- |
| Para quê | Quem usa a **tela** | Um **sistema** falando com outro |
| Como | Matrícula + senha + perfil | Cabeçalho `X-API-Key` |
| Onde vale | `app.py` e telas | `api.py` e `integracao.py` |

Os dois são independentes: a API e a integração não importam nenhum módulo do login, e os outros sistemas **não precisam de matrícula nem de senha**.

---

## 7. Regras das ocorrências

Valores permitidos (`ocorrencia.py`):

| Campo | Valores |
| --- | --- |
| Classificação do defeito | `Critico` · `Maior` · `Menor` |
| Situação do produto | `Aprovado` · `Reprovado` · `Em_reprocesso` |
| Status da ocorrência | `Aberta` · `Em_analise` · `Resolvida` |

Campos obrigatórios: data, hora, classificação, situação, status, produto, estação, tipo de defeito, máquina, usuário, observação e ação realizada (observação e ação não podem ser só espaços). Se algo estiver errado, a tela mostra todos os erros de uma vez e nada é gravado.

---

## 8. Banco de dados

SQLite em `banco/controle_qualidade.db`, com seis tabelas:

```
produto       1 ───── N ocorrencia
estacao       1 ───── N ocorrencia
tipo_defeito  1 ───── N ocorrencia
maquina       1 ───── N ocorrencia
usuario       1 ───── N ocorrencia
```

| Tabela | Campos | Conteúdo inicial |
| --- | --- | --- |
| `produto` | `id_produto`, `numero_serie_produto`, `modelo_produto` | 30 notebooks: `AMT-000001` a `AMT-000030`, modelos AMT N14 a N18 (os mesmos da Rastreabilidade) |
| `estacao` | `id_estacao`, `nome_estacao`, `descricao_estacao` | Embalagem, Inserção Manual, Inspeção de Qualidade, Instalação de Software, Montagem Final, SMT, Teste Funcional |
| `tipo_defeito` | `id_tipo_defeito`, `nome_tipo_defeito`, `descricao_tipo_defeito` | Armazenamento, Bateria, Câmera, Desempenho, Montagem, Software, Teclado, Tela, Touchpad, USB, Wi-Fi, Áudio |
| `maquina` | `id_maquina`, `nome_maquina`, `descricao_maquina` | As TAGs da Manutenção: EMB-01, INS-01, MONT-01, QC-01, SMT-01, SMT-02, SMT-03, TEST-01, TEST-02, TEST-03 |
| `usuario` | `id_usuario`, `nome_usuario`, `perfil_usuario`, `matricula`, `senha_hash`, `ativo`, `data_criacao`, `data_alteracao_senha` | As 4 contas da [seção 6.2](#62-contas-iniciais) (as 5 últimas colunas são criadas pela migração, na primeira abertura da tela) |
| `ocorrencia` | `id_ocorrencia`, data, hora, classificação, situação, observação, ação, status, `visibilidade_ocorrencia` (`Visivel`/`Oculta`) e as cinco chaves estrangeiras | 39 ocorrências, de 19/09/2026 a 02/10/2026 |

O nome da máquina é a **TAG** da Manutenção, e é com ela que o chamado é aberto.

### Scripts do banco

| Script | Para quê | Cuidado |
| --- | --- | --- |
| `criar_banco.py` | Recria o banco do zero com os dados iniciais (no formato anterior ao login) | **Apaga as tabelas e recria.** Não use para iniciar o sistema normalmente. Na próxima abertura da tela, a migração refaz as contas |
| `simular_dados.py` | Gera ocorrências aleatórias para testar dashboard, filtros e histórico (pergunta a quantidade; padrão 50) | Grava no banco em uso |

O banco versionado **não é alterado pelo login**: a migração acontece na primeira abertura da tela, com backup. O banco versionado foi atualizado **no lugar** na OA3 (sem recriar): as 39 ocorrências foram mantidas e continuam ligadas aos mesmos produtos (`AMT-NB001` virou `AMT-000001`, e assim por diante).

### Banco em uso × banco inicial
O banco em uso vem de `QUALIDADE_DB`. Se o arquivo ainda não existir (primeiro início no servidor), o sistema começa com uma **cópia** de `banco/controle_qualidade.db`. Sem a variável, usa o próprio arquivo do projeto.

---

## 9. API da Qualidade

FastAPI, no processo `api.py`, porta **5000**. Documentação interativa em `/docs`.

| Método | Rota | Chave | Função |
| --- | --- | --- | --- |
| GET | `/api/status` | não | Verifica se a API está no ar |
| GET | `/api/ocorrencias` | **sim** | Ocorrências visíveis; filtros opcionais `?de=AAAA-MM-DD&ate=AAAA-MM-DD` (inclusive) |
| GET | `/docs` | não | Documentação interativa |

A chave vai no cabeçalho `X-API-Key` (padrão de demonstração: `amatech-qualidade-demo`; no servidor, `QUALIDADE_API_KEY`). Sem a chave certa, a resposta é **401**. A API é **somente leitura**: não altera nem exclui nada. Ela **não usa o login de usuário**: só a chave.

```bash
curl http://localhost:5000/api/status

curl -H "X-API-Key: amatech-qualidade-demo" \
     "http://localhost:5000/api/ocorrencias?de=2026-10-01&ate=2026-10-31"
```

Exemplo de retorno:

```json
[
  {
    "id_ocorrencia": 1,
    "data_ocorrencia": "2026-09-20",
    "hora_ocorrencia": "08:30:00",
    "produto": "AMT-000001",
    "modelo_produto": "AMT N14",
    "tipo_defeito": "Tela",
    "estacao": "Teste Funcional",
    "maquina": "TEST-01",
    "usuario": "Ana Souza",
    "classificacao_defeito": "Maior",
    "situacao_produto": "Reprovado",
    "observacao_ocorrencia": "Falha na exibição da tela.",
    "acao_realizada": "Produto encaminhado para reprocesso.",
    "status_ocorrencia": "Em_analise"
  }
]
```

### Consumir em Python

```python
import requests
import pandas as pd

URL = "http://IP_DO_COMPUTADOR:5000/api/ocorrencias"
resposta = requests.get(URL, headers={"X-API-Key": "amatech-qualidade-demo"})
resposta.raise_for_status()

df = pd.DataFrame(resposta.json())
print(df["estacao"].value_counts())
```

O consumidor (por exemplo, o Dashboard) **não precisa ter acesso ao arquivo SQLite**. Para outro computador alcançar a API, os dois precisam estar na mesma rede; se não funcionar, confira o IPv4 (`ipconfig`) e o Firewall do Windows. No servidor Docker, o endereço é `http://IP/qualidade/api/...`.

---

## 10. Integração com os outros setores

Toda chamada tem **tempo limite**. Se um sistema estiver fora do ar ou devolver erro, a Qualidade **continua funcionando** e mostra um aviso; a integração nunca derruba o registro da ocorrência.

| Sistema | Endereço padrão | Para quê |
| --- | --- | --- |
| Rastreabilidade | `http://localhost:8000` | Séries e modelos dos notebooks; etapa de cada notebook |
| Manutenção | `http://localhost:5002` | TAGs das máquinas; abertura de chamados |

### 9.1. Cadastros que a Qualidade busca

Ao abrir o sistema (uma vez por sessão) e no botão **Atualizar cadastros dos setores**:

- `GET /api/v1/producoes?limite=1000` na Rastreabilidade → notebooks (série e modelo);
- `GET /api/equipamentos` na Manutenção → máquinas (TAG e nome).

Só o que **falta** é acrescentado; nada é apagado ou alterado. Por isso abrir o sistema não mexe no banco versionado no Git.

### 9.2. O que a Qualidade envia ao registrar uma ocorrência

Cada ocorrência é enviada com `origem_sistema = qualidade` e `id_externo = QLD-<id da ocorrência>`. **Um reenvio não duplica nada.**

**Para a Rastreabilidade** (`POST /api/v1/producoes/{serie}/status`), conforme a situação do produto:

| Situação | O que acontece |
| --- | --- |
| `Reprovado` | O notebook vai para a etapa *Reprovado*. A observação vira a falha (`descricao_falha`) e "tipo de defeito (classificação)" vira o motivo (`motivo_reprovacao`) |
| `Em_reprocesso` | O notebook é reprovado e, em seguida, volta para *Em Montagem* |
| `Aprovado` | O notebook vai para *Aprovado*, **só se** ainda estiver em *Em Fila*, *Em Montagem*, *Em Teste*, *Reprovado* ou *Parado*. Um notebook já aprovado/embalado não volta |

Se a mesma ocorrência já tinha sido informada, a Rastreabilidade responde `"alterado": false` e a tela avisa que a reprovação já estava registrada.

**Para a Manutenção** (`POST /api/manutencao/chamados`), só com a caixa **Abrir chamado na manutenção** marcada:

| Campo do chamado | Valor |
| --- | --- |
| `equipamento_tag` | Máquina da ocorrência |
| `descricao_falha` | `<tipo de defeito> em <série>: <observação> (ocorrência QLD-<id> da Qualidade)` |
| `tipo_manutencao` | `CORRETIVA` |
| `prioridade` | `Critico` → `CRITICA` · `Maior` → `ALTA` · `Menor` → `MEDIA` |

A Manutenção recusa com **409** se a máquina já está parada ou em manutenção (regra RN02 dela); nesse caso a tela mostra o motivo como aviso. Um reenvio com o mesmo `id_externo` devolve o chamado que já existia.

### 9.3. O que o Dashboard lê da Qualidade

`GET /api/ocorrencias?de=&ate=`. Cada ocorrência vira **um defeito de quantidade 1**; ocorrências `Em_reprocesso` também viram retrabalho na Montagem final. O Dashboard só aceita um defeito se houver produção (Aprovado ou Reprovado na Rastreabilidade) no mesmo **dia, turno e modelo** (RN06). A correspondência de nomes entre os sistemas está em [`../dashboard/docs/CADASTROS_COMUNS.md`](../dashboard/docs/CADASTROS_COMUNS.md).

### 9.4. Chaves de API

| Chamada | Chave (`X-API-Key`) |
| --- | --- |
| Qualidade → Rastreabilidade | `amt_demo_qualidade` |
| Qualidade → Manutenção (abrir chamado e listar máquinas) | `amatech-manutencao-demo` |
| Dashboard → Qualidade (API desta pasta) | `amatech-qualidade-demo` |

São chaves só para demonstração; todas podem ser trocadas por variáveis de ambiente.

---

## 11. Variáveis de ambiente

Todas são opcionais.

| Variável | Padrão | Para quê |
| --- | --- | --- |
| `QUALIDADE_API_KEY` | `amatech-qualidade-demo` | Chave que os outros sistemas enviam à API da Qualidade |
| `QUALIDADE_DB` | `banco/controle_qualidade.db` | Caminho do banco em uso (no Docker, um volume) |
| `RASTREABILIDADE_URL` | `http://localhost:8000` | Endereço da Rastreabilidade |
| `RASTREABILIDADE_CHAVE` | `amt_demo_qualidade` | Chave da Qualidade na Rastreabilidade |
| `MANUTENCAO_URL` | `http://localhost:5002` | Endereço da API da Manutenção |
| `MANUTENCAO_CHAVE` | `amatech-manutencao-demo` | Chave da Manutenção |
| `INTEGRACAO_TEMPO_LIMITE` | `3` | Tempo limite, em segundos, de cada chamada aos outros sistemas |
| `QUALIDADE_SENHA_INICIAL` | `amatech1234` | Senha das contas na criação inicial (só vale na migração) |
| `QUALIDADE_SESSAO_MINUTOS` | `30` | Minutos de inatividade até a sessão expirar |

---

## 12. Servidor da rede (Docker)

No servidor, os quatro sistemas ficam no **mesmo IP**, cada um na sua rota, atrás de um proxy (Caddy) na porta 80. Guia completo: [`../SERVIDOR.md`](../SERVIDOR.md).

```bash
# na raiz do repositório
cp .env.exemplo .env          # troque as chaves de API
docker compose up -d --build
```

| Rota | Serviço | Contêiner |
| --- | --- | --- |
| `http://IP/qualidade/` | Tela (Streamlit com `--server.baseUrlPath qualidade`) | `qualidade-tela` |
| `http://IP/qualidade/api/...` · `/qualidade/docs` | API (uvicorn com `--root-path /qualidade`) | `qualidade-api` |

- A imagem instala o `requirements.txt` da **raiz**, que agora inclui `argon2-cffi`; sem ele a tela não sobe. Na primeira abertura da tela no servidor, a migração roda no banco do volume e grava o backup em `/dados/backups/`.
- Os dois contêineres usam o **mesmo volume** (`dados-qualidade`, em `/dados/controle_qualidade.db`), então tela e API enxergam o mesmo banco e os dados **sobrevivem às atualizações**.
- A tela só sobe depois que a API responde `/api/status` (healthcheck).
- Dentro da rede do Docker, a tela chama os outros sistemas pelo nome do serviço (`http://rastreabilidade:8000`, `http://manutencao-api:5002`).
- O horário "agora" do formulário usa o fuso de Manaus (UTC-4), definido na imagem.

---

## 13. Testes

```bash
python -m pytest tests -q        # 59 testes, sem precisar dos outros sistemas no ar
```

| Arquivo | Testes | O que cobre |
| --- | --- | --- |
| `tests/test_api.py` | 4 | `/api/status` sem chave; `/api/ocorrencias` exige chave; filtro por período; banco novo começa com os dados iniciais |
| `tests/test_autenticacao.py` | 25 | Login com as 4 contas e a mesma senha inicial; senha errada, matrícula inexistente e conta inativa; hash Argon2; usuário antigo sem matrícula não entra; criação de usuários (matrícula pelo perfil, só Administrador, validações); sem alterar o próprio perfil; sessão (expiração, logout, conta desativada) |
| `tests/test_permissoes.py` | 13 | Matriz e menu de cada perfil; registrar usa o usuário da sessão e não aceita outro; Almoxarife não registra; editar preserva o responsável; ocultar não apaga; chamado exige permissão própria |
| `tests/test_migracao.py` | 11 | Usuários antigos viram as contas novas com o mesmo id; ocorrências e chaves estrangeiras preservadas; backup; migração repetível sem duplicar; matrículas únicas; só hash no banco; senha alterada não é sobrescrita; API e integração independentes do login |
| `tests/test_integracao.py` | 6 | Cadastros dos setores; reprovação com a falha real; reprocesso (reprova e volta para a montagem); chamado com prioridade pela classificação; sistema fora do ar vira aviso; erro da Manutenção aparece na mensagem |

Os testes da integração usam **respostas HTTP simuladas**, e todos trabalham em bancos temporários, então o banco do projeto não é alterado.

---

## 14. Roteiro de demonstração

0. Entre na Qualidade com `QUA-0001` / `amatech1234` (Inspetor). Com `ALM-0001` o menu só tem Dashboard e Histórico; com `ADM-0001` aparece também **Usuários**.
1. Suba a Rastreabilidade, a Manutenção e a Qualidade. Na barra lateral, **Integração com os setores** mostra quantos notebooks e máquinas foram consultados.
2. Em **Registrar ocorrência**: produto `AMT-000017`, situação *Reprovado*, máquina `TEST-02`, com **Abrir chamado na manutenção** marcado. Use a **hora atual**.
3. A tela mostra o que foi enviado a cada setor.
4. **Rastreabilidade**: o notebook fica *Reprovado*, com a falha informada.
5. **Manutenção**: a `TEST-02` fica *PARADA*, com um chamado aberto pela "Integração".
6. **Dashboard** → *Importação* → *Sincronizar agora*: a produção, os defeitos e a parada aparecem nos indicadores.

---

## 15. Limitações conhecidas

- **Só o registro avisa os outros sistemas.** Editar uma ocorrência no Histórico não reenvia nada à Rastreabilidade nem à Manutenção.
- **Ocultar uma ocorrência** a tira da API, então o Dashboard deixa de enxergá-la na próxima sincronização. Isso não desfaz o que já foi enviado à Rastreabilidade ou à Manutenção.
- **Os cadastros são sincronizados só uma vez por sessão** (ou no botão). Notebooks e máquinas novos dos outros setores só aparecem depois disso.
- **Regra RN06 do Dashboard:** um defeito só é aceito com produção no mesmo dia, turno e modelo. Uma ocorrência registrada com hora muito diferente da real faz o Dashboard recusar todos os defeitos daquele período (a tela dele mostra qual linha causou a recusa). As 39 ocorrências iniciais são de setembro e início de outubro de 2026.
- **Login só na tela.** A API é protegida só pela chave `X-API-Key`, e a lista de ocorrências que ela devolve não depende do perfil de ninguém.
- **Sessão presa à aba:** F5 ou nova aba pede login de novo.
- **Senha inicial compartilhada:** as contas começam com a mesma senha (projeto de aula); o Administrador pode redefini-las na tela Usuários. Não há troca de senha pelo próprio usuário nem bloqueio por tentativas.
- **HTTP no servidor:** o proxy usa a porta 80 sem HTTPS, então a senha digitada trafega sem criptografia na rede local.
- A API é pensada para a rede interna da fábrica e não deve ser exposta diretamente à Internet.

---

## 16. O que mudou desde a primeira versão

| Antes | Agora |
| --- | --- |
| API em **Flask**, iniciada numa thread do Streamlit (só existia com a tela aberta) | API em **FastAPI**, processo próprio, com `/docs` |
| API sem autenticação | `/api/ocorrencias` exige `X-API-Key` |
| Tela na porta 8501 | Tela na **8502** (para os quatro rodarem juntos) |
| Sem comunicação com outros setores | `integracao.py`: busca cadastros, avisa a Rastreabilidade e abre chamado na Manutenção |
| Séries `AMT-NB001`… e máquinas próprias | Séries `AMT-000001`–`AMT-000030` e TAGs da Manutenção, alinhadas com os donos dos dados |
| `GET /api/ocorrencias` sem filtros | Filtros `?de=&ate=` |
| Banco fixo em `banco/` | Banco configurável (`QUALIDADE_DB`), com cópia inicial no primeiro uso |
| Sem testes | 10 testes |
| — | Roda no servidor da rede via Docker (`/qualidade/`) |
| Sem login: o responsável era escolhido no formulário | Login por matrícula e senha, 4 perfis com permissões; o responsável é o usuário logado |
| 4 usuários de exemplo sem acesso individual | Os mesmos 4 viraram contas do sistema (mesmo id, histórico intacto) e há tela para criar usuários |
| 10 testes | 59 testes |

Nenhuma ocorrência foi alterada nem apagada. A API, a integração com os outros setores e as chaves entre sistemas continuam exatamente como estavam.

---

## Documentos relacionados

- [`ESTRUTURA_E_INTEGRACAO.md`](ESTRUTURA_E_INTEGRACAO.md): estrutura e integração desta pasta
- [`../README.md`](../README.md): visão geral do ecossistema
- [`../RESUMO_ALTERACOES.md`](../RESUMO_ALTERACOES.md): alterações da OA3 em todos os setores
- [`../SERVIDOR.md`](../SERVIDOR.md): servidor Docker
- [`../dashboard/docs/CADASTROS_COMUNS.md`](../dashboard/docs/CADASTROS_COMUNS.md): nomes em comum entre os sistemas
