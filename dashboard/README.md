# Dashboard Industrial — AMATECH Smart Factory

Painel único para acompanhar a produção da AMATECH Electronics (fábrica fictícia de notebooks no Polo Industrial de Manaus), com indicadores calculados automaticamente e alertas em semáforo.

Projeto 3 do **Projeto Integrador** da disciplina Ambiente Fabril I · Engenharia da Computação · Fundação Matias Machline · 2026.

## O problema

**Problema 8 — Indicadores dispersos.** Os dados de produção, qualidade, manutenção e perdas ficam em arquivos separados, registrados em papel ou planilha e consolidados manualmente ao fim do turno. Um desvio do início do turno pode levar horas para ser percebido.

## A solução

- Um **banco de dados único**, alimentado por formulários (no momento do evento) e por **planilhas CSV**.
- **Seis indicadores** calculados na hora da consulta: atendimento da meta, produtividade, índice de defeitos, índice de retrabalho, tempo de parada e perdas.
- Um **painel com semáforo** (verde, amarelo e vermelho) e aviso de paradas em andamento.
- **Perfis de acesso**: operador, inspetor, manutenção, supervisor, gestor/diretoria e administrador.

## Andamento

| Etapa | Situação |
| --- | --- |
| OA1 — Diagnóstico e requisitos | Concluída |
| OA2 — Modelagem da solução | Concluída (ver `docs/`) |
| OA3 — Desenvolvimento do MVP | MVP funcionando (10 telas, 40 testes); integração com os outros setores em andamento |

| Sprint | Período | Foco |
| --- | --- | --- |
| S1 | 01/10 a 07/10 | Base do projeto: estrutura, banco, classes de dados, Repositorio |
| S2 | 08/10 a 14/10 | Acesso e cadastros: login, menu por perfil, usuários, cadastros |
| S3 | 15/10 a 21/10 | Registros: produção e metas, qualidade, paradas, perdas |
| S4 | 22/10 a 28/10 | Painel, histórico e importação de CSV |
| S5 | 29/10 a 04/11 | Testes, correções, README, manual de instalação e vídeo |

## Arquitetura

Quatro camadas; cada camada só conversa com a camada logo abaixo.

| Camada | Pasta | Tecnologia |
| --- | --- | --- |
| 1. Apresentação | `app.py`, `pages/` | Streamlit, Plotly |
| 2. Serviços (regras e fórmulas) | `servicos/` | Python, pandas, hashlib |
| 3. Acesso a dados | `acesso_dados/` | sqlite3 |
| 4. Dados | `database/` | SQLite |
| Classes de dados (usadas pelas camadas 1 a 3) | `modelos/` | Python |

![Arquitetura](docs/diagramas/arquitetura_dashboard.png)

## Estrutura do repositório

```
dashboard/
├── app.py              ← tela de login e menu por perfil (entrada do sistema)
├── config.py           ← caminho do banco, fuso horário e endereços dos outros setores
├── pages/              ← telas do Streamlit
├── servicos/           ← regras de negócio e cálculo dos indicadores
├── modelos/            ← as 13 classes de dados
├── acesso_dados/       ← repositorio.py, única parte que escreve SQL
├── database/           ← script SQL do banco (o arquivo .db não vai para o Git)
├── testes/             ← testes das fórmulas e das regras
├── docs/               ← relatório da OA2, diagramas, wireframes e planejamento
├── requirements.txt
└── README.md
```

## Como executar

```bash
# 1. Criar e ativar um ambiente virtual
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/Mac: source .venv/bin/activate

# 2. Instalar as bibliotecas
pip install -r requirements.txt

# 3. Abrir o sistema no navegador (http://localhost:8501)
streamlit run app.py
```

Na primeira execução, o banco `database/banco.db` é criado automaticamente a partir de `database/banco_dashboard_industrial.sql`, já com os dados do exemplo do enunciado (15/08/2026). Para recomeçar do zero, basta apagar o arquivo `banco.db`. Outro caminho pode ser escolhido pela variável de ambiente `DASHBOARD_DB`.

### Usuários de teste

Somente para testes; trocar as senhas antes de qualquer uso real.

| Login | Senha | Perfil | Telas |
| --- | --- | --- | --- |
| `supervisor` | `super123` | Supervisor de produção | Todas, exceto Usuários; em Cadastros, só os limites do semáforo |
| `gestor` | `gestor123` | Gestor/Diretoria | Painel e Histórico |
| `operador` | `oper123` | Operador de estação | Produção e Qualidade (defeitos) |
| `inspetor` | `insp123` | Inspetor de qualidade | Qualidade (defeitos e retrabalho) |
| `manutencao` | `manut123` | Manutenção | Paradas |
| `admin` | `admin123` | Administrador | Cadastros e Usuários |

### Testes

```bash
python -m pytest testes -q
```

### Importação de planilhas

Os modelos ficam em `database/modelos_csv/` e também podem ser baixados na tela de Importação. Separador `;`, datas em DD/MM/AAAA. Uma única linha inválida recusa o arquivo inteiro, e a tela lista linha, coluna e problema de cada erro (RN06).

### Sincronização com os outros setores (OA3)

Na tela **Importação**, a seção *Sincronizar com os setores* busca os dados dos outros sistemas da fábrica pelas APIs deles:

| Setor | Sistema | Vira no Dashboard |
| --- | --- | --- |
| Rastreabilidade | `http://localhost:8000` (`/api/v1/passagens`, `/api/v1/produtos`) | Produção por dia, turno e modelo: cada Aprovado ou Reprovado é uma unidade |
| Qualidade | `http://localhost:5000` (`/api/ocorrencias`) | Um defeito por ocorrência; reprocesso também gera retrabalho na Montagem final |
| Manutenção | `http://localhost:5002` (`/api/manutencao/chamados`, `/api/equipamentos`) | Uma parada por chamado (da abertura ao fim do atendimento); máquinas |

Cada setor é gravado como uma importação, com as mesmas regras da planilha: um registro inválido recusa só aquele setor (RN06), e a tela lista linha, coluna e problema. Sincronizar de novo atualiza os registros, sem duplicar. Horários em UTC são convertidos para o horário de Manaus; eventos fora dos turnos aparecem como ignorados. Um sistema fora do ar aparece como aviso.

Os endereços e a chave da Rastreabilidade ficam em `config.py` e podem ser trocados pelas variáveis `RASTREABILIDADE_URL`, `RASTREABILIDADE_CHAVE`, `QUALIDADE_URL` e `MANUTENCAO_URL`. A correspondência de nomes entre os sistemas está em [`docs/CADASTROS_COMUNS.md`](docs/CADASTROS_COMUNS.md).

## Documentação

| Documento | Arquivo |
| --- | --- |
| Relatório da OA2 (modelagem completa) | [`docs/relatorio_oa2.md`](docs/relatorio_oa2.md) |
| Contexto do projeto para integração com outros sistemas | [`docs/contexto_projeto_dashboard_industrial.md`](docs/contexto_projeto_dashboard_industrial.md) |
| MER, casos de uso, classes, fluxo e arquitetura (.png e .drawio) | [`docs/diagramas/`](docs/diagramas/) |
| Wireframes das 10 telas | [`docs/wireframes/`](docs/wireframes/) |
| Planejamento da OA3 | [`docs/planejamento/`](docs/planejamento/) |

Os arquivos `.drawio` abrem em [diagrams.net](https://app.diagrams.net) (Arquivo → Abrir de → Dispositivo).

## Equipe

| Integrante | Papel |
| --- | --- |
| Letícia | Líder; coordenação, revisão do código e autenticação |
| Vinicius | Analista de processos; regras de negócio e importação de CSV |
| Mateus | Desenvolvedor; banco de dados e cálculo dos indicadores |
| Radier | Desenvolvedor de interface; as 10 telas em Streamlit |
| Jose Orlando | Testes e documentação |
