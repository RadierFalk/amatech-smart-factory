# Integração com os outros projetos da sala

O sistema foi preparado para dois tipos de integração:

| Tipo | Quando usar | Como |
|---|---|---|
| **A. Pela API** (recomendado) | Cada equipe mantém o seu banco/sistema e conversa por HTTP | `/api/v1/...` com chave `X-API-Key` |
| **B. Banco único** | A sala decide juntar tudo num só arquivo `.db` | Migrações idempotentes + `tools/verificar_conflitos.py` |

Os dois podem coexistir: o banco é único e, mesmo assim, as outras equipes podem usar a API.

---

## A. Integração pela API (contrato `v1`)

Documentação interativa (precisa de internet para carregar o visual): `http://SERVIDOR:8000/docs`

### 1. Criar a chave de um sistema
Entre como **MAT-0001 (Administrador)** → módulo **Cadastros → Integrações → Novo sistema**, informe o nome
(ex.: `qualidade`). A chave (`amt_...`) aparece **uma única vez** — copie e entregue à outra equipe.
Só o *hash* é guardado; se perder, use *Gerar nova chave*. Dá para desativar um sistema sem apagá-lo.

**Chaves de demonstração do ecossistema (OA3).** Para a demonstração com os outros sistemas da sala, o sistema
cria ao iniciar três clientes, se ainda não existirem: `qualidade` (`amt_demo_qualidade`), `dashboard`
(`amt_demo_dashboard`) e `manutencao` (`amt_demo_manutencao`). Um cliente que já existe nunca é alterado: se o
administrador gerar uma chave nova, ela continua valendo. As chaves podem ser trocadas pelas variáveis de ambiente
(tabela abaixo), e `AMATECH_CHAVES_DEMO=0` desliga a criação. São só para a demonstração, como a `amatech-iot-demo`.

### 2. Chamar
Todas as chamadas (menos `/saude`) levam o cabeçalho `X-API-Key: amt_...`.

| Método | Rota | Para quê |
|---|---|---|
| GET | `/api/v1/saude` | Testar se está no ar (sem chave) |
| GET | `/api/v1/status-producao` | Lista de etapas e ordem do fluxo |
| GET | `/api/v1/produtos` | Modelos de notebook e seus componentes (BOM) |
| GET | `/api/v1/componentes` | Componentes e estoque |
| GET | `/api/v1/producoes?atualizado_apos=...&status=...&limite=200&offset=0` | Produções (filtro incremental por data) |
| GET | `/api/v1/producoes/{numero_serie}` | Uma produção, com histórico e NCs |
| POST | `/api/v1/producoes/{numero_serie}/status` | Outro sistema muda a etapa: `{"status":"Em Teste","maquina":"BANCADA-03"}`. Ao reprovar, pode mandar a falha real: `{"status":"Reprovado","descricao_falha":"...","motivo_reprovacao":"...","id_externo":"QLD-15"}` (veja abaixo) |
| GET | `/api/v1/passagens?de=...&ate=...&status=...&limite=5000` | Histórico de etapas de todas as produções no período (`de`/`ate` em ISO 8601, UTC). Inclui o histórico de demonstração, que a fila de eventos não tem |
| POST | `/api/v1/nao-conformidades` | Registrar falha: `{"numero_serie":"AMT-000012","descricao_falha":"...","motivo_reprovacao":"...","id_externo":"QLD-77"}` |
| GET | `/api/v1/solicitacoes?status=PENDENTE` | Solicitações de material |
| GET | `/api/v1/eventos?apos_id=0&limite=100&tipo=...` | Fila de eventos (veja abaixo) |

Exemplo:
```bash
curl -H "X-API-Key: amt_SUA_CHAVE" http://localhost:8000/api/v1/producoes?limite=5
curl -X POST -H "X-API-Key: amt_SUA_CHAVE" -H "Content-Type: application/json" \
     -d '{"status":"Em Teste","maquina":"BANCADA-03"}' \
     http://localhost:8000/api/v1/producoes/AMT-000012/status
```

### Reprovação vinda de outro sistema

Quando o corpo de `POST /api/v1/producoes/{numero_serie}/status` traz `"status": "Reprovado"`, a não conformidade
é gravada com `descricao_falha` e `motivo_reprovacao` (sem eles, continua o texto padrão "Reprovado automaticamente
pela máquina"), com `origem_sistema` = nome do cliente da chave e com o `id_externo`. Se já existe uma NC com o
mesmo `id_externo` desse sistema, a reprovação não é aplicada de novo e a resposta vem com `"alterado": false`.
Assim, a Qualidade não precisa chamar também `POST /api/v1/nao-conformidades` (isso geraria NC duplicada).

Exemplo de resposta de `/api/v1/passagens`:
```json
[{"numero_serie": "AMT-000004", "modelo": {"codigo": "N16-I7-16-512", "nome": "AMT N16"}, "status": "Aprovado",
  "em": "2026-10-20T14:32:00Z", "origem": "MANUAL"}]
```

### Convenções do contrato
- **Chave de negócio entre sistemas = `numero_serie`** (ex.: `AMT-000012`), nunca o `id` interno.
- Campos em português; datas em **ISO-8601 UTC com "Z"** (`2026-10-19T14:30:00Z`). O banco guarda em UTC; a tela converte para Manaus (UTC-4).
- Mudanças de status feitas por outro sistema ficam no histórico com origem `API:<nome do sistema>`.
- NC externa com o mesmo `(sistema, id_externo)` **não duplica** — pode reenviar sem medo.
- Erros vêm como `{"detail": "mensagem em português"}` com código HTTP (401 chave inválida, 404 não achou, 409 conflito, 422 dado inválido).

### Eventos (como saber que algo mudou sem ficar consultando tudo)
Cada ação importante grava um evento numa fila (`integracao_eventos`). O outro sistema guarda o `ultimo_id`
que recebeu e pergunta só o que veio depois: `GET /api/v1/eventos?apos_id=<ultimo_id>`.

Tipos: `producao.criada`, `producao.etapa_alterada`, `nao_conformidade.registrada`, `solicitacao.criada`,
`baixa.registrada`, `estoque.alterado`, `componente.atualizado`.

### Máquinas / IoT (rota antiga, mantida)
`POST /api/maquinas/status` com `X-API-Key: <AMATECH_API_KEY>` (padrão de demonstração `amatech-iot-demo`).
**Troque a chave** antes de apresentar: veja variáveis de ambiente abaixo.

---

## B. Unir os bancos num só arquivo

### Como o sistema se comporta com um banco que já existe
- Ao iniciar, aplica só as migrações que faltam (`database/migracoes/*.sql`, controle na tabela `_migracoes`).
- Usa `CREATE TABLE IF NOT EXISTS` — **nunca apaga nem recria** tabelas existentes.
- Os dados de demonstração só entram se o arquivo `.db` for **novo**. Em banco já existente não insere nada.
- Se achar uma tabela com o **mesmo nome** mas sem as colunas de que precisa, **para com uma mensagem clara** em vez de falhar no meio do uso.
- Para apontar para o banco compartilhado: variável `AMATECH_DB` (veja abaixo).

### Passo a passo
1. **Cada equipe faz backup** do seu `.db` (copiar o arquivo).
2. **Verifique conflitos** com o banco da outra equipe:
   ```
   python tools/verificar_conflitos.py ..\outra_equipe\banco.db
   ```
   Mostra tabelas de mesmo nome, colunas diferentes e FKs deles que apontam para tabelas nossas.
3. **Combine quem é dono de cada tabela “mestre”**. Sugestão para a sala:

   | Tabela | Dona sugerida | Observação |
   |---|---|---|
   | `usuarios` | Uma só equipe (a que fizer login) | Todos referenciam `usuarios.id`; `matricula` é única |
   | `produtos`, `componentes`, `produto_componentes` | Rastreabilidade (nós) | Outras equipes só leem ou referenciam `idprd`/`idcmp` |
   | `producoes`, `historico_passagem`, `nao_conformidades` | Rastreabilidade (nós) | Chave externa: `numero_serie_notebook` |
   | `solicitacoes_materiais`, `baixas_materiais` | Rastreabilidade (nós) | |
   | Tabelas de outras áreas (qualidade, logística, ...) | A equipe de cada uma | Só precisam de FK para `producoes(id)` ou usar `numero_serie` |

4. **Resolva conflito de nome**: a equipe que *não* for dona renomeia a tabela (ex.: `usuarios` → `usuarios_qualidade`) ou passa a usar a tabela da dona.
   Tabelas com colunas a mais são aceitas (o nosso sistema ignora as extras); o que não pode é faltar coluna obrigatória.
5. **Copiar as tabelas da outra equipe para o banco unido** (exemplo; ajuste os nomes):
   ```sql
   -- no sqlite3 / DB Browser, abrindo o banco da dona (o nosso):
   ATTACH DATABASE 'C:/caminho/outra_equipe.db' AS outra;
   -- recrie a estrutura (copie o CREATE TABLE do script deles) e depois:
   INSERT INTO inspecoes SELECT * FROM outra.inspecoes;
   DETACH DATABASE outra;
   ```
   O ideal é que cada equipe passe a **criar suas tabelas por migração** (`003_qualidade.sql`, `004_logistica.sql`...), com `IF NOT EXISTS`,
   na mesma pasta `database/migracoes/` — assim o banco unido nasce certo em qualquer máquina. **Use números de versão diferentes** (o prefixo numérico do arquivo).
6. **Ligue as FKs** de preferência por `producoes.id` (ou `numero_serie_notebook`, que é único) e `usuarios.id`.
7. Inicie o sistema apontando para o banco unido e teste login + uma produção.

> Ligações entre tabelas de equipes diferentes devem ter `PRAGMA foreign_keys = ON` (o sistema já liga a cada conexão).

---

## Variáveis de ambiente

| Variável | Para quê | Padrão |
|---|---|---|
| `AMATECH_DB` | Caminho do arquivo `.db` (use para o banco unido) | `database/amatech.db` |
| `AMATECH_API_KEY` | Chave da rota de máquinas/IoT | `amatech-iot-demo` |
| `AMATECH_CHAVES_DEMO` | `0` desliga a criação das chaves de demonstração do ecossistema | `1` |
| `AMATECH_CHAVE_QUALIDADE`, `AMATECH_CHAVE_DASHBOARD`, `AMATECH_CHAVE_MANUTENCAO` | Chaves de demonstração de cada sistema | `amt_demo_qualidade`, `amt_demo_dashboard`, `amt_demo_manutencao` |
| `AMATECH_CORS` | Origens liberadas para outro front-end, separadas por vírgula (`http://localhost:3000,http://192.168.0.20:8501`) | vazio |
| `AMATECH_FUSO` | Fuso em horas para exibição | `-4` |

PowerShell (Windows), exemplo:
```powershell
$env:AMATECH_DB = "C:\sala\banco_unico.db"
$env:AMATECH_API_KEY = "uma-chave-forte"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Acesso pela rede da sala
Inicie com `--host 0.0.0.0` e passe aos colegas `http://<SEU-IP>:8000` (descubra o IP com `ipconfig`).
Libere a porta 8000 no Firewall do Windows se perguntar.
