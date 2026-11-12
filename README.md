# AMATECH — ERP Industrial Modular Unificado

Sistema ERP integrado da fábrica de notebooks **AMATECH**, consolidando os subsistemas setoriais em **uma única aplicação, uma única porta (`8501`) e um único login corporativo**, mantendo a identidade visual oficial (`identidade/amatech.py`).

---

## Arquitetura Modular Integrada (Porta Única)

Ao contrário de múltiplos sistemas isolados rodando em portas diferentes e exigindo senhas separadas, o ERP AMATECH unifica a navegação e as regras de negócio num único processo (`app.py`):

1. **Login Único Corporativo**: O colaborador informa sua matrícula funcional e senha uma única vez.
2. **Sincronização Automática de Sessão**: O motor de integração (`portal/integracao_local.py`) provisiona e sincroniza automaticamente o perfil do usuário nos bancos dos módulos e compartilha a sessão autenticada.
3. **Seletor de Módulos Pós-Login (RBAC)**: Exibe exclusivamente os cartões dos módulos que a persona do usuário logado tem poder para acessar.
4. **Navegação Interna & Integração In-Process**: Ao selecionar um módulo, as telas e funcionalidades abrem dentro do próprio sistema, e toda a comunicação entre Rastreabilidade, Qualidade, Manutenção e Dashboard ocorre diretamente em memória (`AMATECH_INTEGRACAO_LOCAL=1`).

| Módulo | Sigla | Código Base Reutilizado | Escopo Principal |
|--------|-------|-------------------------|------------------|
| **1. Rastreabilidade e Materiais** | `RAS` | `rastreabilidade/app/servicos/` | Terminal do operador, ordens seriadas (`AMT-...`), avanço de etapas, solicitações e baixas de estoque (BOM) e relatórios CSV |
| **2. Controle da Qualidade** | `QLD` | `qualidade/` | Dashboard estatístico, registro/edição/ocultação de ocorrências de defeitos e integração com Rastreabilidade e Manutenção |
| **3. Gestão da Manutenção** | `MNT` | `manutencao/` | Painel de máquinas por estação (TAGs), chamados corretivos, Ordens de Serviço (O.S.), preventivas, MTTR/MTBF e peças |
| **4. Dashboard Industrial** | `DSH` | `dashboard/` | Indicadores consolidados (meta, defeitos, retrabalho, produtividade, paradas, perdas), semáforo de alertas e sincronização |
| **5. Gestão de Usuários** | `USR` | `portal/` | Cadastro central de colaboradores, atribuição de personas, ativação/bloqueio, redefinição de senha e matriz RBAC |

---

## Matriz de Personas e Poder de Acesso

Todas as contas de demonstração utilizam a senha única **`amatech1234`**:

| Matrícula | Colaborador | Persona | Módulos Visíveis no Seletor | Poderes de Acesso por Módulo |
|-----------|-------------|---------|-----------------------------|------------------------------|
| `ADM-0001` | Ana Souza | **Administrador** | `RAS`, `QLD`, `MNT`, `DSH`, `USR` (**5**) | Acesso total administrativo, cadastros mestres, auditoria e gestão de usuários |
| `GES-0001` | Orlando Vandres | **Supervisor / Gestor** | `RAS`, `QLD`, `MNT`, `DSH` (**4**) | Painel de indicadores, metas, perdas, sincronização, gestão de O.S. e relatórios |
| `OPE-0001` | João Silva | **Operador de Produção** | `RAS`, `QLD`, `MNT`, `DSH` (**4**) | Terminal/avanço de série (`RAS`), apontamento de defeito (`QLD`/`DSH`), produção do turno (`DSH`) e abertura de chamado (`MNT`) |
| `QUA-0001` | Maria Santos | **Inspetor de Qualidade** | `RAS`, `QLD`, `DSH` (**3**) | Registro/edição/ocultação de ocorrências (`QLD`), retrabalho (`DSH`), consulta de série e não conformidade (`RAS`) |
| `TEC-2001` | João Lima Silva | **Técnico de Manutenção** | `MNT`, `DSH` (**2**) | Fila de chamados, execução de O.S., preventivas e indicadores (`MNT`), início/encerramento de paradas (`DSH`) |
| `ALM-0001` | Carlos Oliveira | **Almoxarife** | `RAS`, `QLD` (**2**) | Solicitações e baixas de material no estoque, componentes BOM (`RAS`) e consulta de reprovações (`QLD`) |

---

## Demonstração da nova versão (Angular + FastAPI + PostgreSQL)

Sobe o ERP novo completo numa máquina só, com dados de exemplo dos últimos 7 dias. Só precisa do Docker.

| Sistema | Subir | Parar | Apagar os dados |
|---|---|---|---|
| Windows | `iniciar-demo.bat` (duplo clique) | `iniciar-demo.bat parar` | `iniciar-demo.bat zerar` |
| Linux / macOS | `./iniciar-demo.sh` | `./iniciar-demo.sh parar` | `./iniciar-demo.sh zerar` |

- Abre em **http://localhost:8080**. Contas: `ADM-0001`, `GES-0001`, `OPE-0001`, `QUA-0001`, `TEC-2001`, `ALM-0001`, senha `amatech1234`.
- A primeira subida faz o build das imagens e leva alguns minutos; as seguintes são rápidas.
- Windows sem Docker Desktop, com o Docker dentro do WSL: o `.bat` usa o WSL sozinho. Deixe a janela aberta durante a demonstração; fechar encerra o acesso.
- Só para demonstração: segredos de desenvolvimento e dados fictícios. Produção: `SERVIDOR_ERP.md`.

---

## Como Executar

### Opção 1: Script PowerShell (Recomendado no Windows)

```powershell
.\iniciar.ps1
```

### Opção 2: Comando Direto Streamlit

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
```

Acesse em **`http://localhost:8501`**.

---

## Testes Automatizados

```powershell
# Suíte do ERP Unificado (RBAC, Isolamento de Módulos, Integração In-Process e UI AppTest)
.\.venv\Scripts\python.exe -m pytest portal/tests -v
```
