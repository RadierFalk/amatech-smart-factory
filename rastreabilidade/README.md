# AMATECH — Sistema de Rastreabilidade de Produtos

Projeto Integrador *Ambiente Fabril I — AMATECH Smart Factory* · Projeto 2 · Problema 5 (controle do fluxo de materiais).

**Stack:** Python + FastAPI + SQLite (`sqlite3` puro) · front-end HTML/CSS/JS sem dependências externas (funciona offline, on-premises).

## O que o sistema faz
- **Terminal do Operador**: login por matrícula/senha/turno, painel com KPIs, produções recentes e alertas de estoque crítico.
- **Cadastros** (telas no estilo TOTVS RM: faixa de opções, grade com filtro/ordenação, ícones Novo/Editar/Excluir):
  Produtos (com aba **Componentes** para vincular/alterar/remover componentes do notebook), Componentes, Status de produção, Usuários, Integrações.
- **Produção**: nova produção (gera nº de série `AMT-000031`), avançar etapa, reprovação com não conformidade, histórico completo.
- **Materiais**: solicitações geradas a partir da lista de componentes do produto, baixas pelo Almoxarife com controle de saldo e estoque.
- **Relatórios**: produção, estoque, materiais e não conformidades — imprimir ou exportar CSV (abre no Excel).
- **API de integração** `/api/v1` para os outros projetos da sala — veja [docs/INTEGRACAO.md](docs/INTEGRACAO.md).

## Passo a passo no VS Code (Windows)

### 1. Pré-requisitos
- **Python 3.10 ou mais novo** — https://www.python.org/downloads/ (marque **“Add python.exe to PATH”** na instalação).
- **VS Code** com a extensão *Python* (Microsoft).

### 2. Abrir o projeto
1. Descompacte o `amatech-rastreabilidade.zip`.
2. No VS Code: **File → Open Folder…** e escolha a pasta `amatech-rastreabilidade`.
3. Abra o terminal: **Terminal → New Terminal** (PowerShell).

### 3. Criar o ambiente virtual e instalar
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
> Se o PowerShell bloquear o `Activate.ps1`: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tente de novo (ou use o terminal *Command Prompt* e `.venv\Scripts\activate.bat`).
> No VS Code, se aparecer “Select interpreter”, escolha o Python de `.venv`.

### 4. Rodar
```powershell
python -m uvicorn app.main:app --reload
```
Abra **http://127.0.0.1:8000** no navegador. Na primeira execução o banco `database/amatech.db` é criado sozinho, já com dados de demonstração.

### 5. Entrar
Senha de todos: **`amatech123`**

| Matrícula | Perfil | Pode |
|---|---|---|
| `MAT-00421` | Operador (Carlos) | Produção, avançar etapas, solicitar materiais |
| `MAT-0100` | Almoxarife (Ana) | Tudo do operador + **dar baixa** de material |
| `MAT-0200` | Inspetor de Qualidade (Rafael) | Reprovar / registrar não conformidade |
| `MAT-0001` | Administrador | Tudo, + status, usuários e **Integrações** |

### 6. Roteiro de demonstração (2–3 min)
1. Entre como `MAT-00421` → painel com KPIs e **estoque crítico** (Bateria 45Wh).
2. **Cadastros → Produtos** → duplo clique no modelo → aba **Componentes** → *Vincular componente* / *Alterar quantidade* → **OK**.
3. **Produção → Nova produção** → escolha o modelo → *Solicitar materiais do produto*.
4. Selecione uma produção “Em Fila” → **Avançar etapa**.
5. Saia e entre como `MAT-0100` → **Materiais → Solicitações** → *Dar baixa* (o estoque diminui).
6. **Relatórios** → gerar → imprimir / exportar CSV.
7. Como `MAT-0001` → **Integrações → Novo sistema** → mostra a chave da API para outra equipe.

## Comandos úteis
| O que | Comando |
|---|---|
| Rodar os testes | `python -m unittest discover -s tests -v` |
| Zerar o banco e recarregar a demonstração | Pare o servidor e rode `python -m app.seed` |
| Acessar de outro computador da sala | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` → `http://SEU-IP:8000` |
| Documentação interativa da API | http://127.0.0.1:8000/docs (precisa de internet para carregar o visual) |
| Verificar conflito com o banco de outra equipe | `python tools/verificar_conflitos.py outro.db` |

## Problemas comuns
- **`python` não é reconhecido** → reinstale o Python marcando *Add to PATH*, ou use `py` no lugar de `python`.
- **`No module named 'fastapi'`** → o ambiente virtual não está ativo (aparece `(.venv)` no começo da linha do terminal) ou faltou o `pip install -r requirements.txt`.
- **Porta 8000 ocupada** → use `--port 8001`.
- **Quero começar do zero** → feche o servidor e apague `database/amatech.db`; ele é recriado ao iniciar.
- **Esqueci a senha do admin** → `python -m app.seed` recria o banco de demonstração (apaga os dados!).

## Estrutura
```
app/
  main.py            entrada FastAPI (rotas, erros, arquivos estáticos)
  config.py          configurações e variáveis de ambiente
  db.py, migracoes.py conexão SQLite e migrações idempotentes
  seguranca.py       senha (PBKDF2), sessões, perfis
  seed.py            dados de demonstração
  schemas.py         validação das entradas (Pydantic)
  servicos/          regras de negócio (sem HTTP)
  routers/           rotas HTTP finas (/api/..., /api/v1/...)
database/migracoes/  001_base.sql (script do banco da equipe), 002_integracao.sql
static/              telas (index.html, css, js/telas/*)
tests/               testes automatizados
tools/               verificar_conflitos.py
docs/INTEGRACAO.md   contrato da API e união de bancos
```

## Mapa de requisitos
Todos os RF001–RF017 e RNF001–RNF006 do documento de requisitos são atendidos pelas telas/rotas acima
(RNF003: API desacoplada do front-end; RNF004: roda on-premises sem internet; RNF de desempenho: consultas indexadas).

## Limitações conhecidas
- Sessões ficam em memória: reiniciar o servidor desloga todos.
- “Estoque crítico” usa o limite fixo de 50 unidades (`ESTOQUE_CRITICO` em `app/config.py`).
- O campo **Quantidade** de Produtos é tratado como meta/lote planejado.
- Senhas de demonstração e a chave `amatech-iot-demo` devem ser trocadas fora da apresentação.
