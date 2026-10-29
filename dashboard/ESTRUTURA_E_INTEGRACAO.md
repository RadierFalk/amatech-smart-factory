# Dashboard Industrial: estrutura e integração (OA3)

**Função:** painel central de indicadores · **Projeto 3 → Problema 8** (indicadores dispersos) · Pasta no repositório
único: `dashboard/`

Este documento resume como o sistema está organizado hoje, o que foi feito na OA3 e como ele conversa com os outros
três sistemas da AMATECH Smart Factory. O resumo de todos os setores está em
[`../RESUMO_ALTERACOES.md`](../RESUMO_ALTERACOES.md); a modelagem completa (MER, regras, telas e fórmulas), em
`docs/relatorio_oa2.md`.

## 1. O sistema

| Item | Valor |
| --- | --- |
| Tecnologia | Python + Streamlit + Plotly + pandas + SQLite (`sqlite3` puro) |
| Porta | **8501** |
| Banco | `database/banco.db`, criado na primeira execução a partir de `database/banco_dashboard_industrial.sql` (fora do Git) |
| Dono dos cadastros | Estações, turnos, tipos de defeito, motivos de parada, metas e limites do semáforo |
| Executar | `streamlit run app.py` → http://localhost:8501 (ex.: `supervisor` / `super123`) |
| Testes | `python -m pytest testes -q` (46 testes) |

## 2. Estrutura atual

Quatro camadas; cada uma só conversa com a camada logo abaixo.

```
dashboard/
├── app.py                   ← camada 1: login (T01) e menu com as telas do perfil (st.navigation)
├── pages/                   ← camada 1: telas T02 a T10
│   ├── comum.py             ← permissões, formatação brasileira, cartões do semáforo e filtros
│   ├── 1_Painel.py          ← T02: seis indicadores, semáforo, paradas em andamento e gráficos
│   ├── 2_Producao_e_metas.py, 3_Qualidade.py, 4_Paradas.py, 5_Perdas.py   ← T03 a T06: registros
│   ├── 6_Importacao.py      ← T07: planilhas CSV e "Sincronizar com os setores"
│   ├── 7_Historico.py       ← T08: quatro abas e download em CSV
│   ├── 8_Cadastros.py       ← T09: listas editáveis e limites do semáforo
│   └── 9_Usuarios.py        ← T10
├── servicos/                ← camada 2: regras de negócio e fórmulas
│   ├── registro.py          ← ServicoRegistro: valida (RN01–RN09) e grava; upsert por origem_sistema + id_externo
│   ├── calculadora.py       ← CalculadoraIndicadores: os seis indicadores de um período
│   ├── alertas.py           ← AvaliadorAlertas: cor do semáforo pelos limites (RN08)
│   ├── importador_csv.py    ← ImportadorCSV: tudo ou nada (RN06); entrada também da sincronização
│   ├── conector_ecossistema.py ← ConectorEcossistema: lê as APIs dos outros setores
│   ├── cadastros.py, cadastros_comuns.py ← listas e tradução dos nomes dos outros setores (sinônimos)
│   ├── autenticacao.py, historico.py, filtro.py, formatos.py, erros.py
├── acesso_dados/repositorio.py ← camada 3: único lugar que executa SQL; transações
├── modelos/entidades.py     ← as 13 classes de dados
├── database/                ← camada 4: script SQL e modelos de planilha (modelos_csv/)
├── testes/                  ← conftest.py (banco temporário por teste) e 4 arquivos de teste
├── docs/                    ← relatório da OA2, contexto, diagramas, wireframes e CADASTROS_COMUNS.md
├── config.py                ← caminho do banco, fuso (UTC-4) e endereços dos outros sistemas
└── .streamlit/config.toml   ← porta 8501
```

## 3. O que foi feito na OA3

No início da OA3, o repositório tinha só a documentação da OA2. Todo o código foi escrito agora, seguindo a modelagem:

| Etapa | Conteúdo |
| --- | --- |
| Banco | Colunas `origem_sistema` e `id_externo` em `registro_producao`, `defeito`, `retrabalho` e `parada` (índice único parcial); seis usuários de teste, um por perfil; tipos de defeito em comum com a Qualidade |
| Camadas 2 a 4 | Repositório, entidades e serviços (registro, indicadores, semáforo, autenticação, cadastros, histórico) |
| Importação CSV | Modelos para download, prévia, erros por linha e coluna, tudo ou nada (RN06) |
| Telas | T01 a T10 conforme os wireframes, com menu por perfil |
| Integração | `ConectorEcossistema` e a seção "Sincronizar com os setores" na T07 |
| Testes | 46 testes, incluindo os casos de referência do enunciado (94,7%, 4,2%, 215,7 un/h) |

## 4. Comunicação com os outros sistemas

O Dashboard **só consome** APIs; não expõe nenhuma e não lê o banco de ninguém.

```
Rastreabilidade (8000) ──/api/v1/produtos, /api/v1/passagens──┐
Qualidade (5000)       ──/api/ocorrencias?de=&ate=────────────┼──► ConectorEcossistema ──► ImportadorCSV ──► banco
Manutenção (5002)      ──/api/equipamentos, /api/manutencao/chamados┘
```

Ordem de cada sincronização (período escolhido na T07; padrão, últimos 7 dias):

| Passo | De onde | O que vira | Identificador (`id_externo`) |
| --- | --- | --- | --- |
| 1. Cadastros | Rastreabilidade `/api/v1/produtos`; Manutenção `/api/equipamentos` | Produtos (modelos) e máquinas (setor → estação pelos sinônimos) | (nome / TAG) |
| 2. Produção | Rastreabilidade `/api/v1/passagens` (chave `amt_demo_dashboard`) | Um registro por dia, turno e modelo: realizada = Aprovados + Reprovados | `AAAA-MM-DD\|<turno>\|<modelo>` |
| 3. Defeitos | Qualidade `/api/ocorrencias` | Um defeito por ocorrência (quantidade 1); Em_reprocesso também gera retrabalho na Montagem final | `QLD-<id>` |
| 4. Paradas | Manutenção `/api/manutencao/chamados` | Uma parada por chamado (abertura → fim do atendimento); sem fim = em andamento | `MNT-<id>` |

Regras:
- **Cada setor é uma importação** pelo `ImportadorCSV`: um registro inválido recusa só aquele setor (RN06), e a tela
  mostra linha, coluna e problema.
- Sincronizar de novo **atualiza** os registros (ex.: um chamado concluído preenche o fim da parada), sem duplicar.
- Horários em UTC são convertidos para Manaus (UTC-4). Eventos fora dos turnos (06h–14h e 14h–22h) e chamados
  cancelados aparecem como **ignorados**, sem erro.
- **Um defeito precisa de produção no mesmo dia, turno e modelo**; sem ela, o setor da Qualidade é recusado (RN06).
- Sistema fora do ar aparece como aviso; os outros setores continuam.
- A tradução dos nomes ("Testes Funcionais" = "Teste funcional", "Teclado" = "Falha no teclado"...) está em
  `servicos/cadastros_comuns.py` e documentada em `docs/CADASTROS_COMUNS.md`.

## 5. Variáveis de ambiente

| Variável | Padrão |
| --- | --- |
| `DASHBOARD_DB` | `database/banco.db` |
| `RASTREABILIDADE_URL` / `RASTREABILIDADE_CHAVE` | `http://localhost:8000` / `amt_demo_dashboard` |
| `QUALIDADE_URL` | `http://localhost:5000` |
| `MANUTENCAO_URL` | `http://localhost:5002` |
| `DASHBOARD_TEMPO_LIMITE` | `5` segundos |

## 6. Como conferir

```bash
python -m pytest testes -q
streamlit run app.py
```

Com os outros três sistemas no ar: entre como `supervisor` / `super123` → **Importação** → *Sincronizar agora*. Cada setor
mostra o resultado; depois, o **Painel** exibe a produção, os defeitos e as paradas em andamento vindos dos setores.
