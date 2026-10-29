# AMATECH Smart Factory: ecossistema integrado

Projeto Integrador · *Ambiente Fabril I* · Engenharia da Computação · Fundação Matias Machline · 2026.

Quatro sistemas da fábrica fictícia AMATECH Electronics (notebooks, Polo Industrial de Manaus), feitos por equipes
diferentes, reunidos num só repositório e **conversando pelas APIs** uns dos outros. Isso responde ao problema da
"ausência de integração entre setores" (enunciado, seção 1.2).

| Pasta | Setor | Projeto | Tecnologia | Portas |
| --- | --- | --- | --- | --- |
| [`rastreabilidade/`](rastreabilidade/) | Rastreabilidade e fluxo de materiais | Projeto 2 → Problema 5 | FastAPI + HTML/JS + SQLite | 8000 |
| [`dashboard/`](dashboard/) | Painel central de indicadores | Projeto 3 → Problema 8 | Streamlit + Plotly + SQLite | 8501 |
| [`qualidade/`](qualidade/) | Qualidade (testes e inspeção) | Projeto 4 → Problema 3 | Streamlit + Flask + SQLite | 8502 (tela) · 5000 (API) |
| [`manutencao/`](manutencao/) | Manutenção | Projeto 5 → Problema 4 | Streamlit + FastAPI + SQLite | 8503 (tela) · 5002 (API) |

Cada pasta tem um **`ESTRUTURA_E_INTEGRACAO.md`** com a estrutura do sistema, o que mudou na OA3 e com quem ele
conversa. O resumo das alterações por setor está em [`RESUMO_ALTERACOES.md`](RESUMO_ALTERACOES.md).

## Como os sistemas conversam

Cada sistema mantém o **próprio banco** e só fala com os outros por HTTP. Ninguém lê o banco de ninguém.

```
                       séries e etapas do notebook
  Rastreabilidade ◄──────────────────────────────── Qualidade ──── chamado (defeito da máquina) ───► Manutenção
       (8000)        reprovado / reprocesso / aprovado  (5000)                                         (5002)
          │                                               │                                             │
          │ produção (Aprovados + Reprovados)             │ defeitos e retrabalho                       │ paradas
          └──────────────────────────────►  Dashboard Industrial (8501)  ◄──────────────────────────────┘
```

| Dados | Dono | Quem usa |
| --- | --- | --- |
| Modelos de notebook e números de série | Rastreabilidade | Qualidade, Dashboard |
| Máquinas (TAGs) | Manutenção | Qualidade, Dashboard |
| Ocorrências de defeito | Qualidade | Rastreabilidade (etapa do notebook), Manutenção (chamado), Dashboard |
| Chamados de manutenção | Manutenção | Dashboard (paradas) |
| Estações, turnos, metas e indicadores | Dashboard | — |

Todo dado enviado a outro sistema leva `origem_sistema` + `id_externo` (ex.: `qualidade` + `QLD-15`), então um reenvio
atualiza em vez de duplicar. A correspondência de nomes entre os sistemas ("Testes Funcionais" = "Teste funcional")
está em [`dashboard/docs/CADASTROS_COMUNS.md`](dashboard/docs/CADASTROS_COMUNS.md).

## Como executar os quatro juntos (Windows)

```powershell
# 1. Uma vez: ambiente virtual com as bibliotecas dos quatro sistemas
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 2. Sobe os quatro sistemas, cada um numa janela
powershell -ExecutionPolicy Bypass -File iniciar.ps1
```

| Sistema | Endereço | Login de teste |
| --- | --- | --- |
| Rastreabilidade | http://localhost:8000 | `MAT-0001` / `amatech123` (Administrador) |
| Dashboard | http://localhost:8501 | `supervisor` / `super123` |
| Qualidade | http://localhost:8502 | (sem login) |
| Manutenção | http://localhost:8503 | `GES-0001` / `123456` (Gestor) |

O `requirements.txt` da raiz reúne as bibliotecas dos quatro, em versões testadas juntas. Cada pasta também tem o seu,
para rodar o sistema sozinho.

### Roteiro de demonstração

1. **Qualidade** → *Registrar ocorrência*: produto `AMT-000017`, situação *Reprovado*, máquina `TEST-02`, com
   *Abrir chamado na manutenção* marcado. A tela mostra o que foi enviado a cada setor.
2. **Rastreabilidade**: o notebook fica *Reprovado*, com a falha informada na não conformidade.
3. **Manutenção**: a `TEST-02` fica *PARADA*, com um chamado aberto pela "Integração".
4. **Dashboard** → *Importação* → *Sincronizar agora*; no **Painel**, a produção, os defeitos e a parada em andamento
   aparecem nos indicadores.

Registre a ocorrência com a **hora atual**: o Dashboard só aceita um defeito se houver produção no mesmo dia, turno e
modelo (RN06).

## Testes

```powershell
cd rastreabilidade; ..\.venv\Scripts\python -m pytest -q; cd ..      # 37 testes
cd manutencao;      ..\.venv\Scripts\python -m pytest -q; cd ..      # 10 testes
cd qualidade;       ..\.venv\Scripts\python -m pytest tests -q; cd .. # 6 testes
cd dashboard;       ..\.venv\Scripts\python -m pytest testes -q; cd .. # 46 testes
```

## Histórico do repositório

Cada pasta foi importada do repositório original da equipe com todo o histórico de commits e autores (`git subtree`).
Os commits antigos usam os caminhos originais (sem o prefixo da pasta); para ver o histórico de um sistema, use
`git log -- <pasta>/` a partir da importação ou `git log` completo.

| Pasta | Repositório de origem | Branch importado |
| --- | --- | --- |
| `rastreabilidade/` | github.com/waddington-rendryo-text/amatech-rastreabilidade | `integracao-ecossistema` |
| `qualidade/` | github.com/LlyanDarc/SistemaControleQualidadeDefeitos | `integracao-ecossistema` |
| `manutencao/` | github.com/Vandrekad/management-control | `integracao-ecossistema` |
| `dashboard/` | github.com/RadierFalk/amatech-dashboard-industrial | `mvp` |
