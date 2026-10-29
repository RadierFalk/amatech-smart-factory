# Controle da Qualidade: estrutura e integração (OA3)

**Setor:** Qualidade (testes e inspeção) · **Projeto 4 → Problema 3** · Pasta no repositório único: `qualidade/`

Este documento resume como o sistema está organizado hoje, o que foi alterado para a integração da OA3 e como ele
conversa com os outros três sistemas da AMATECH Smart Factory. O resumo de todos os setores está em
[`../RESUMO_ALTERACOES.md`](../RESUMO_ALTERACOES.md).

## 1. O sistema

| Item | Valor |
| --- | --- |
| Tecnologia | Python + Streamlit (telas) + Flask (API) + SQLite + matplotlib |
| Portas | Telas **8502** · API **5000** (sobe junto com as telas) |
| Banco | `banco/controle_qualidade.db` (está no Git) |
| Dono dos cadastros | **Ocorrências de defeito**. Notebooks vêm da Rastreabilidade; máquinas, da Manutenção |
| Executar | `streamlit run app.py` → http://localhost:8502 (API em http://localhost:5000) |
| Testes | `python -m pytest tests -q` (6 testes; não precisam dos outros sistemas no ar) |

## 2. Estrutura atual

```
qualidade/
├── app.py                   ← entrada do Streamlit; sobe a API Flask numa thread; menu; busca os cadastros dos setores
├── api.py                   ← API Flask: GET /api/status e GET /api/ocorrencias?de=&ate=
├── integracao.py            ← NOVO: conversa com a Rastreabilidade e a Manutenção
├── banco.py                 ← todas as consultas SQL (inclui as funções usadas pela integração)
├── ocorrencia.py            ← validação e regras das ocorrências
├── indicadores.py, graficos.py ← cálculos e gráficos do dashboard da Qualidade
├── criar_banco.py           ← recria o banco do zero com os dados iniciais
├── simular_dados.py         ← gera ocorrências aleatórias para demonstração
├── telas/
│   ├── dashboard.py
│   ├── registro_ocorrencia.py ← registro + opção "Abrir chamado na manutenção"
│   └── historico_ocorrencias.py
├── banco/controle_qualidade.db
├── tests/test_integracao.py ← NOVO
├── .streamlit/config.toml   ← NOVO: porta 8502
└── requirements.txt         ← + requests
```

## 3. O que foi alterado na OA3

| Alteração | Arquivos |
| --- | --- |
| **`integracao.py`**: busca os notebooks e as máquinas nos setores donos e avisa os outros sistemas quando uma ocorrência é registrada. Toda chamada tem tempo limite; **sistema fora do ar vira aviso**, nunca erro | `integracao.py` (novo) |
| Barra lateral com o resultado da busca dos cadastros e o botão **Atualizar cadastros dos setores** | `app.py` |
| Tela de registro: opção **Abrir chamado na manutenção (defeito causado pela máquina)** e avisos do que foi enviado | `telas/registro_ocorrencia.py` |
| API: filtros `?de=AAAA-MM-DD&ate=AAAA-MM-DD` em `/api/ocorrencias` | `api.py` |
| Funções de banco para a integração (ocorrência detalhada, inserir notebook e máquina sem duplicar) | `banco.py` |
| **Cadastros alinhados com os donos**: séries `AMT-000001` a `AMT-000030` (modelos AMT N14 a N18, como na Rastreabilidade) e as TAGs da Manutenção (+ SMT-02, SMT-03, TEST-03, EMB-01) | `criar_banco.py`, `banco/controle_qualidade.db` |
| Porta 8502, `requests`, testes e seção 9 do README | `.streamlit/config.toml`, `requirements.txt`, `tests/`, `README.md` |

O banco do repositório **foi atualizado no lugar, sem recriar**: as 39 ocorrências foram mantidas e continuam ligadas
aos mesmos produtos (AMT-NB001 virou AMT-000001, e assim por diante).

## 4. Comunicação com os outros sistemas

```
                 GET /api/v1/producoes (séries)       ┌──────────────────────┐
Qualidade ───────────────────────────────────────────►│ Rastreabilidade 8000 │
   │      POST /api/v1/producoes/{serie}/status ─────►└──────────────────────┘
   │
   │      GET  /api/equipamentos (TAGs)               ┌──────────────────────┐
   ├─────────────────────────────────────────────────►│ Manutenção 5002      │
   │      POST /api/manutencao/chamados ─────────────►└──────────────────────┘
   │
   ▲      GET /api/ocorrencias?de=&ate=               ┌──────────────────────┐
   └──────────────────────────────────────────────────│ Dashboard 8501       │
                                                      └──────────────────────┘
```

**O que a Qualidade envia ao registrar uma ocorrência** (identificador `QLD-<id da ocorrência>`):

| Situação do produto | Rastreabilidade |
| --- | --- |
| Reprovado | Etapa *Reprovado*, com a observação como falha e "tipo de defeito (classificação)" como motivo |
| Em_reprocesso | *Reprovado* e, em seguida, *Em Montagem* |
| Aprovado | *Aprovado*, se o notebook ainda não passou por essa etapa (não volta um notebook já embalado) |

Com a opção de chamado marcada, a Manutenção recebe um chamado para a máquina da ocorrência, com prioridade pela
classificação: Crítico → CRITICA, Maior → ALTA, Menor → MEDIA. Reenvios não duplicam nada.

**O que o Dashboard lê:** `GET /api/ocorrencias?de=&ate=`. Cada ocorrência vira um defeito de quantidade 1 no
Dashboard; *Em_reprocesso* também vira retrabalho na Montagem final.

| Chamada | Chave (`X-API-Key`) |
| --- | --- |
| Rastreabilidade | `amt_demo_qualidade` |
| Manutenção (abrir chamado) | `amatech-manutencao-demo` |
| API da Qualidade (lida pelo Dashboard) | sem chave |

## 5. Variáveis de ambiente

| Variável | Padrão |
| --- | --- |
| `RASTREABILIDADE_URL` / `RASTREABILIDADE_CHAVE` | `http://localhost:8000` / `amt_demo_qualidade` |
| `MANUTENCAO_URL` / `MANUTENCAO_CHAVE` | `http://localhost:5002` / `amatech-manutencao-demo` |
| `INTEGRACAO_TEMPO_LIMITE` | `3` segundos |

## 6. Como conferir

1. Suba a Rastreabilidade e a Manutenção; depois `streamlit run app.py`.
2. Na barra lateral, *Integração com os setores* mostra quantos notebooks e máquinas foram consultados.
3. Registre uma ocorrência **Reprovado** para `AMT-000017`, máquina `TEST-02`, com a opção de chamado marcada.
4. A tela mostra os avisos; na Rastreabilidade o notebook fica *Reprovado* e na Manutenção a TEST-02 fica *PARADA*.
