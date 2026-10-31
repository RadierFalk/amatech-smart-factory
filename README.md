# AMATECH Smart Factory: Ecossistema Integrado

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162-green?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.66-red?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Engine%20%7C%20Swarm-2496ED?logo=docker)
![Status](https://img.shields.io/badge/Testes-109%20passed-brightgreen)
![Instituição](https://img.shields.io/badge/FMM-Engenharia%20da%20Computa%C3%A7%C3%A3o-darkblue)

**Fundação Matias Machline · Engenharia da Computação · 2026**  
*Projeto Integrador · Ambiente Fabril I (OA3)*

</div>

---

## 📌 1. Visão Geral do Projeto

Este projeto consolida a integração horizontal dos quatro sistemas da fábrica fictícia **AMATECH Electronics** (fabricante de notebooks sediada no Polo Industrial de Manaus - PIM). Originalmente desenvolvidos por equipes independentes, os módulos foram unificados neste monorepo para solucionar o problema central de **"ausência de integração entre setores"** (Enunciado do Projeto Integrador, Seção 1.2).

### 🏭 Módulos do Ecossistema

| Pasta | Setor / Domínio | Projeto Origem | Stack Tecnológica | Rota no Servidor | Portas Locais |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`rastreabilidade/`](rastreabilidade/) | **Rastreabilidade e Materiais** | Projeto 2 → Problema 5 | FastAPI · HTML5/Vanilla JS · SQLite | `/rastreabilidade/` | `8000` (Web e API) |
| [`qualidade/`](qualidade/) | **Controle da Qualidade** | Projeto 4 → Problema 3 | Streamlit · FastAPI · SQLite | `/qualidade/` | `8502` (Tela) · `5000` (API) |
| [`manutencao/`](manutencao/) | **Gestão da Manutenção** | Projeto 5 → Problema 4 | Streamlit · FastAPI · SQLite | `/manutencao/` | `8503` (Tela) · `5002` (API) |
| [`dashboard/`](dashboard/) | **Dashboard Industrial** | Projeto 3 → Problema 8 | Streamlit · FastAPI · Plotly · SQLite | `/dashboard/` | `8501` (Tela) · `5003` (API) |

Cada diretório mantém sua própria documentação detalhada em `ESTRUTURA_E_INTEGRACAO.md`. O histórico de alterações da integração está documentado em [`RESUMO_ALTERACOES.md`](RESUMO_ALTERACOES.md).

---

## 🏗️ 2. Arquitetura e Comunicação entre Setores

Adotou-se o padrão **Database-per-Service**: cada setor é dono estrito dos seus dados e mantém seu próprio banco SQLite. Nenhuma aplicação acessa diretamente o banco de outra; toda a troca de informações ocorre **exclusivamente via APIs REST síncronas**.

```
                        séries e etapas do notebook
   Rastreabilidade ◄──────────────────────────────── Qualidade ──── chamado (defeito da máquina) ───► Manutenção
     (Porta 8000)      reprovado / reprocesso / aprovado (Porta 5000)                                   (Porta 5002)
          │                                               │                                             │
          │ produção (Aprovados + Reprovados)             │ defeitos e retrabalho                       │ paradas
          └──────────────────────────────►  Dashboard Industrial (8501)  ◄──────────────────────────────┘
```

### Matriz de Responsabilidade de Dados

| Entidade de Dados | Setor Proprietário (Single Source of Truth) | Consumidores |
| :--- | :--- | :--- |
| **Modelos de Notebook e Números de Série** | Rastreabilidade | Qualidade, Dashboard Industrial |
| **Máquinas e Ativos Fabris (TAGs)** | Manutenção | Qualidade, Dashboard Industrial |
| **Ocorrências de Não Conformidade e Defeitos** | Qualidade | Rastreabilidade (etapa), Manutenção (chamados), Dashboard |
| **Chamados e Paradas de Máquina** | Manutenção | Dashboard Industrial (OEE / Paradas) |
| **Indicadores, Metas e Turnos** | Dashboard Industrial | Gestão Geral / Supervisão |

### Idempotência e Rastreabilidade Cruzada
Toda requisição intersetorial trafega com os campos de rastreabilidade:
* `origem_sistema` (ex.: `"qualidade"`)
* `id_externo` (ex.: `"QLD-15"`, `"MNT-42"`, `"2026-10-30|1|AMT-A"`)

Graças a esse padrão, reenvios de chamados ou sincronizações repetidas atualizam registros existentes sem gerar duplicidade.

### Segurança por Perímetro de Rede (*Zero-Key Internal Trust*)
* **Chamadas Internas (S2S):** As chamadas entre containers na rede Docker privada (ou em `localhost`) operam sob modelo de perímetro confiável, **sem necessidade de configuração manual de chaves no `.env`**.
* **Chamadas Externas:** Requisições provenientes de clientes desconhecidos que enviem chave incorreta recebem `401 Unauthorized`.
* **Modo Estrito (Opcional):** É possível ativar a exigência de chave em qualquer serviço definindo `<SISTEMA>_EXIGIR_CHAVE=1`.

---

## 🚀 3. Como Rodar Localmente (Ambiente de Desenvolvimento)

Recomendado para avaliação do código, execução rápida no Windows e desenvolvimento.

### Pré-requisitos
* **Python 3.12+** instalado.
* **PowerShell 5.1+** (padrão no Windows 10/11).
* Git.

---

### Passo a Passo Rápido (Automatizado)

1. **Clone o repositório:**
   ```powershell
   git clone https://github.com/RadierFalk/amatech-smart-factory.git
   cd amatech-smart-factory
   ```

2. **Crie o ambiente virtual e instale as dependências unificadas:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install -r requirements.txt
   ```

3. **Inicie todos os sistemas com um comando:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File iniciar.ps1
   ```
   > O script inicializará as 4 telas e as 4 APIs em janelas minimizadas na barra de tarefas.

---

### Passo a Passo Manual (Terminal a Terminal)

Se preferir rodar cada serviço individualmente em terminais separados:

```powershell
# Ative o ambiente virtual em cada terminal antes de rodar o comando:
.\.venv\Scripts\Activate.ps1

# 1. Rastreabilidade (Telas + API na porta 8000)
cd rastreabilidade; python -m uvicorn app.main:app --port 8000

# 2. Manutenção - API (porta 5002)
cd manutencao; python -m uvicorn api:app --port 5002

# 3. Qualidade - API (porta 5000)
cd qualidade; python -m uvicorn api:app --port 5000

# 4. Dashboard - API (porta 5003)
cd dashboard; python -m uvicorn api:app --port 5003

# 5. Qualidade - Tela Streamlit (porta 8502)
cd qualidade; python -m streamlit run app.py --server.port 8502

# 6. Manutenção - Tela Streamlit (porta 8503)
cd manutencao; python -m streamlit run app.py --server.port 8503

# 7. Dashboard - Tela Streamlit (porta 8501)
cd dashboard; python -m streamlit run app.py --server.port 8501
```

---

### 🌐 Endereços e Credenciais de Teste

| Aplicação | Interface Web (Frontend) | Documentação da API (Swagger) | Usuário de Teste | Senha de Teste | Perfil |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Rastreabilidade** | [http://localhost:8000](http://localhost:8000) | [http://localhost:8000/docs](http://localhost:8000/docs) | `MAT-0001` | `amatech123` | Administrador |
| **Qualidade** | [http://localhost:8502](http://localhost:8502) | [http://localhost:5000/docs](http://localhost:5000/docs) | *(Acesso livre)* | *(Sem senha)* | Inspetor |
| **Manutenção** | [http://localhost:8503](http://localhost:8503) | [http://localhost:5002/docs](http://localhost:5002/docs) | `GES-0001` | `123456` | Gestor |
| **Dashboard Industrial**| [http://localhost:8501](http://localhost:8501) | [http://localhost:5003/docs](http://localhost:5003/docs) | `supervisor` | `super123` | Supervisor |

> **Para encerrar a execução local:** Feche as janelas minimizadas abertas pelo script `iniciar.ps1`.

---

## 🌐 4. Como Rodar Remotamente (Servidor / Produção com Docker)

No servidor, os serviços rodam encapsulados em contêineres Docker integrados diretamente ao Traefik na rede `VandreNet`, unificando todos os acessos sob um único domínio com HTTPS e roteamento nativo por caminhos (`/rastreabilidade`, `/qualidade`, `/manutencao`, `/dashboard`).

### Cenários Suportados:
1. **Docker Swarm / Portainer:** Deploy através de Stack com Traefik na rede `VandreNet`.
2. **Servidor Local / WSL 2 (Ubuntu):** Docker Engine padrão (conforme detalhado no [`SERVIDOR.md`](SERVIDOR.md)).

---

### Passo a Passo de Deploy Remoto

1. **Clone o repositório no servidor:**
   ```bash
   git clone https://github.com/RadierFalk/amatech-smart-factory.git
   cd amatech-smart-factory
   ```

2. **Configure o arquivo `.env` (Opcional):**
   Copie o modelo de exemplo:
   ```bash
   cp .env.exemplo .env
   ```
   > Graças à arquitetura de rede confiável, você **não precisa gerar chaves de integração**. O `.env` serve apenas para parâmetros de rede do host:
   ```env
   AMATECH_HOST=amatech.automakad.com.br
   PORTA=80
   ```

3. **Se for utilizar Docker Swarm com Traefik (Rede externa VandreNet):**
   Caso a rede externa `VandreNet` ainda não exista, crie-a uma única vez:
   ```bash
   docker network create --driver overlay --attachable VandreNet
   ```

4. **Inicie a stack dos serviços:**
   ```bash
   # Opção A: Docker Compose padrão
   docker compose up -d --build

   # Opção B: Docker Swarm / Portainer
   docker stack deploy -c docker-compose.yml amatech
   ```

5. **Verifique o status da execução:**
   ```bash
   docker compose ps
   ```
   *Todos os serviços devem reportar status `running`, e os endpoints de healthcheck das APIs devem estar `healthy`.*

---

### 🗺️ Mapeamento de Rotas no Traefik

O Traefik encaminha o tráfego a partir do domínio configurado:

| Rota Externa | Destino Interno | Descrição |
| :--- | :--- | :--- |
| `https://<DOMINIO>/` | Redirecionamento | Redireciona automaticamente para o Dashboard Central (`/dashboard/`) |
| `https://<DOMINIO>/rastreabilidade/` | `rastreabilidade:8000` | Interface web e API de rastreabilidade |
| `https://<DOMINIO>/qualidade/` | `qualidade-tela:8502` | Painel Streamlit do Controle de Qualidade |
| `https://<DOMINIO>/qualidade/api/` | `qualidade-api:5000` | API REST do Controle de Qualidade |
| `https://<DOMINIO>/manutencao/` | `manutencao-tela:8503` | Painel Streamlit do Controle da Manutenção |
| `https://<DOMINIO>/manutencao/api/`| `manutencao-api:5002` | API REST do Controle da Manutenção |
| `https://<DOMINIO>/dashboard/` | `dashboard-tela:8501` | Painel Streamlit do Dashboard Industrial |
| `https://<DOMINIO>/dashboard/api/` | `dashboard-api:5003` | API REST de Indicadores do Dashboard |

> Guia aprofundado com configuração de IP fixo, firewall do Windows/WSL2 e rotinas de backup de banco de dados: consulte o arquivo **[`SERVIDOR.md`](SERVIDOR.md)**.

---

## 🧪 5. Roteiro de Demonstração Funcional da Integração

Para demonstrar a interoperabilidade entre os quatro sistemas (critério avaliativo da OA3):

1. **Abrir a tela da Qualidade** (`http://localhost:8502` ou `/qualidade/`):
   * Vá em **Registrar ocorrência**.
   * Selecione o notebook `AMT-000017`.
   * Defina a situação como **Reprovado** e informe a máquina `TEST-02`.
   * Marque a opção **Abrir chamado na manutenção**.
   * Clique em salvar. A tela exibirá a confirmação de envio para a Rastreabilidade e Manutenção.
2. **Verificar a Rastreabilidade** (`http://localhost:8000` ou `/rastreabilidade/`):
   * Consulte o notebook `AMT-000017`.
   * Observe que o status mudou para **Reprovado** e a Não Conformidade foi anexada com o ID externo da Qualidade.
3. **Verificar a Manutenção** (`http://localhost:8503` ou `/manutencao/`):
   * O equipamento `TEST-02` passou para status **PARADA**.
   * Um chamado de prioridade Crítica/Alta foi aberto automaticamente em nome do operador de serviço de integração.
4. **Verificar o Dashboard Industrial** (`http://localhost:8501` ou `/dashboard/`):
   * No menu lateral, acesse **Importação** e clique em **Sincronizar agora**.
   * Acesse a página **Painel**: os dados de produção atualizados, o novo defeito computado no índice de qualidade e a parada operacional da máquina `TEST-02` estarão refletidos em tempo real nos gráficos e semáforos de meta.

---

## ✅ 6. Testes Automatizados

O repositório possui uma suíte com **109 testes automatizados** via `pytest`, cobrindo regras de negócio (RNs), persistência SQLite e contratos de API de todas as equipes:

```powershell
# Execução da suíte completa de testes:
cd rastreabilidade; ..\.venv\Scripts\python -m pytest -q; cd ..      # 37 testes
cd manutencao;      ..\.venv\Scripts\python -m pytest -q; cd ..      # 11 testes
cd qualidade;       ..\.venv\Scripts\python -m pytest tests -q; cd .. # 10 testes
cd dashboard;       ..\.venv\Scripts\python -m pytest testes -q; cd .. # 51 testes
```

---

## 👥 7. Equipe e Repositórios de Origem

Este monorepo foi estruturado através do mecanismo de `git subtree`, preservando todo o histórico de commits, autoria e rastreabilidade dos branches originais:

| Módulo / Setor | Repositório Original no GitHub | Branch Integrado |
| :--- | :--- | :--- |
| **Rastreabilidade** | `github.com/waddington-rendryo-text/amatech-rastreabilidade` | `integracao-ecossistema` |
| **Qualidade** | `github.com/LlyanDarc/SistemaControleQualidadeDefeitos` | `integracao-ecossistema` |
| **Manutenção** | `github.com/Vandrekad/management-control` | `integracao-ecossistema` |
| **Dashboard** | `github.com/RadierFalk/amatech-dashboard-industrial` | `mvp` |

---
<div align="center">
Desenvolvido como parte das avaliações do curso de Engenharia da Computação · FMM 2026.
</div>
