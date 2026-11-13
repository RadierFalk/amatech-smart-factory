# Servidor da AMATECH Smart Factory (Docker Swarm + Traefik) · sistema antigo

> **Legado.** A produção agora é o ERP novo (API única + Angular + PostgreSQL): `docker-compose.yml`, guia
> [SERVIDOR_ERP.md](SERVIDOR_ERP.md). Este guia e o `docker-compose.legado.yml` ficam para voltar atrás na virada
> (SERVIDOR_ERP.md, seção 5) e como referência dos volumes `amatech_dados-*`, de onde a migração lê os dados antigos.

Este guia publica os quatro sistemas num servidor com **Docker Swarm** (pela linha de comando ou pelo Portainer),
atrás do **Traefik**, com **um domínio, HTTPS e uma rota para cada sistema**. Quem acessa o domínio usa as telas pelo
navegador, e outros programas leem os dados pelas APIs.

```
navegadores e programas
            │  https://<DOMINIO>/...
            ▼
Traefik (entrypoint websecure, certificado Let's Encrypt)  ── rede VandreNet (overlay) ──
    /                      → redireciona para /dashboard/
    /rastreabilidade/      → rastreabilidade   (telas + API, 8000)
    /qualidade/            → qualidade-tela    (8502)
    /qualidade/api/...     → qualidade-api     (5000)
    /manutencao/           → manutencao-tela   (8503)
    /manutencao/api/...    → manutencao-api    (5002)
    /dashboard/            → dashboard-tela    (8501)
    /dashboard/api/...     → dashboard-api     (5003)
```

Cada sistema guarda o banco SQLite num volume do Docker. Entre si, os sistemas se falam pela rede `VandreNet`, pelo
nome do serviço (ex.: `http://rastreabilidade:8000`). Nenhuma porta dos serviços é publicada no servidor: o único
caminho de fora para dentro é o Traefik.

## 1. Rotas

| Endereço | O que é |
| --- | --- |
| `https://<DOMINIO>/` | Redireciona para o Dashboard |
| `https://<DOMINIO>/rastreabilidade/` | Rastreabilidade (login `MAT-0001` / `amatech123`) |
| `https://<DOMINIO>/qualidade/` | Controle da Qualidade |
| `https://<DOMINIO>/manutencao/` | Controle da Manutenção (login `GES-0001` / `123456`) |
| `https://<DOMINIO>/dashboard/` | Dashboard Industrial (login `supervisor` / `super123`) |
| `https://<DOMINIO>/<sistema>/docs` | Documentação interativa da API de cada sistema |

| API | Exemplos | Chave (`X-API-Key`) |
| --- | --- | --- |
| Rastreabilidade | `/rastreabilidade/api/v1/producoes`, `/rastreabilidade/api/v1/passagens?de=&ate=` | criada na tela *Cadastros → Integrações* (ou as de demonstração) |
| Qualidade | `/qualidade/api/ocorrencias?de=AAAA-MM-DD&ate=AAAA-MM-DD` | `QUALIDADE_API_KEY` |
| Manutenção | `/manutencao/api/equipamentos`, `/manutencao/api/manutencao/chamados`, `/manutencao/api/manutencao/indicadores` | `MANUTENCAO_API_KEY` |
| Dashboard | `/dashboard/api/indicadores?de=&ate=&turno=&produto=`, `/dashboard/api/graficos`, `/dashboard/api/paradas-em-andamento` | `DASHBOARD_API_KEY` |

As rotas `/api/status` (e `/rastreabilidade/api/v1/saude`) não pedem chave: servem para testar se o sistema está no ar.

### Chaves e perímetro de rede

- **Entre contêineres** (rede `VandreNet`) ou em `localhost`, as chamadas dispensam a chave. É assim que a Qualidade
  avisa a Rastreabilidade e a Manutenção, e que o Dashboard sincroniza os setores.
- **Pelo Traefik**, a chave é obrigatória. O Traefik acrescenta o cabeçalho `X-Forwarded-For` a toda requisição de
  fora, e as APIs recusam com `401` quem chega assim sem chave (ou com a chave errada).
- **Modo estrito:** `<SISTEMA>_EXIGIR_CHAVE=1` no `.env` exige a chave também na rede interna.

## 2. Pré-requisitos

O `docker-compose.legado.yml` é uma *stack* do Swarm e depende de uma infraestrutura que já deve existir no servidor:

| Item | Valor esperado |
| --- | --- |
| Docker em modo Swarm | `docker info` mostra `Swarm: active` (senão, `docker swarm init`) |
| Rede overlay externa | `VandreNet` (crie uma vez: `docker network create --driver overlay --attachable VandreNet`) |
| Traefik na rede `VandreNet` | Provedor Swarm ativo, entrypoint `websecure` (443) e certresolver `letsencryptresolver` |
| DNS | O domínio de `AMATECH_HOST` apontando para o IP do servidor |
| Imagem | `ghcr.io/radierfalk/amatech-smart-factory:latest`, publicada pelo GitHub Actions a cada push na `main` |

> As regras do Traefik estão em `deploy.labels`, que só valem no Swarm. Por isso `docker compose up` **não** publica
> os sistemas. Para rodar sem Swarm, use o `iniciar.ps1` (seção 8).

## 3. Instalar

### Pela linha de comando

```bash
git clone https://github.com/RadierFalk/amatech-smart-factory.git
cd amatech-smart-factory
cp .env.exemplo .env && nano .env    # domínio e chaves (o .env não vai para o Git)
set -a; . ./.env; set +a             # o docker stack deploy não lê o .env sozinho
docker stack deploy -c docker-compose.legado.yml amatech
docker stack services amatech        # todos devem chegar a 1/1
```

### Pelo Portainer

*Stacks → Add stack*, cole o `docker-compose.legado.yml` (ou aponte para o repositório) e cadastre as variáveis do
`.env.exemplo` em *Environment variables*.

Na primeira subida, cada sistema cria o seu banco no volume com os dados de demonstração. Teste em
`https://<DOMINIO>/`.

> **Chaves da Rastreabilidade:** ficam no banco dela. As de demonstração (`amt_demo_qualidade`, `amt_demo_dashboard`)
> são criadas na primeira subida. Para trocar, use a tela *Cadastros → Integrações → Gerar nova chave*. Só é preciso
> pôr a chave nova no `.env` (`RASTREABILIDADE_CHAVE_QUALIDADE` ou `RASTREABILIDADE_CHAVE_DASHBOARD`) se o modo
> estrito da Rastreabilidade estiver ligado.

## 4. Usar as APIs de outro computador

PowerShell:
```powershell
$chave = @{ "X-API-Key" = "amatech-dashboard-demo" }
Invoke-RestMethod "https://amatech.automakad.com.br/dashboard/api/indicadores?de=2026-10-01&ate=2026-10-31" -Headers $chave
```

Python:
```python
import requests
r = requests.get("https://amatech.automakad.com.br/qualidade/api/ocorrencias", params={"de": "2026-10-01"},
                 headers={"X-API-Key": "amatech-qualidade-demo"}, timeout=5)
print(r.json())
```

Troque as chaves de demonstração pelas do `.env` do servidor.

## 5. Operação do dia a dia

Os nomes dos serviços levam o prefixo da stack (`amatech_`).

| Tarefa | Comando |
| --- | --- |
| Ver o estado | `docker stack services amatech` e `docker stack ps amatech` |
| Ver os registros de um sistema | `docker service logs -f amatech_qualidade-tela` (ou outro serviço) |
| Reiniciar um sistema | `docker service update --force amatech_manutencao-api` |
| **Atualizar** para a versão nova | Depois que o GitHub Actions publicar a imagem: `git pull`, carregar o `.env` e repetir o `docker stack deploy` (os dados ficam nos volumes) |
| **Cópia de segurança** dos bancos | `docker run --rm -v amatech_dados-qualidade:/dados -v "$PWD/backup":/backup alpine tar czf /backup/qualidade.tgz -C /dados .` (e o mesmo para `dados-rastreabilidade`, `dados-manutencao` e `dados-dashboard`) |
| Parar tudo | `docker stack rm amatech` (os volumes continuam) |
| Apagar os dados e recomeçar com a demonstração | `docker stack rm amatech`, `docker volume rm amatech_dados-rastreabilidade amatech_dados-qualidade amatech_dados-manutencao amatech_dados-dashboard` e um novo `docker stack deploy` |

Serviços: `rastreabilidade`, `qualidade-api`, `qualidade-tela`, `manutencao-api`, `manutencao-tela`, `dashboard-api`,
`dashboard-tela`.

## 6. Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| `network VandreNet not found` | Crie a rede (seção 2) ou confira o nome da rede do Traefik |
| `this node is not a swarm manager` | O Docker não está em modo Swarm (`docker swarm init`) ou o comando foi rodado num nó *worker* |
| Serviço em `0/1` | `docker service ps --no-trunc amatech_<serviço>` mostra o erro; `docker service logs amatech_<serviço>` mostra os registros |
| Domínio responde 404 do Traefik | Confira `AMATECH_HOST` (ele precisa estar carregado no deploy) e se o Traefik enxerga a rede `VandreNet` |
| Certificado inválido | O DNS ainda não aponta para o servidor, ou o certresolver do Traefik não se chama `letsencryptresolver` |
| `401` ao chamar uma API de fora | Esperado sem chave: envie `X-API-Key` com o valor do `.env` |
| Sincronização do Dashboard mostra "fora do ar" | O serviço do outro sistema parou: `docker stack services amatech` |
| Horários com 4 horas de diferença | Os contêineres usam o horário de Manaus (UTC-4); confira o relógio do servidor |

## 7. Segurança

- Troque as chaves de demonstração no `.env` antes de liberar o acesso: elas estão escritas neste repositório.
- As APIs só dispensam a chave para chamadas internas; tudo o que passa pelo Traefik precisa dela.
- A tela da Qualidade não tem login (o sistema original não tinha); as outras três têm. Com o domínio público,
  qualquer pessoa que souber o endereço usa essa tela.
- Os bancos ficam nos volumes do Docker. Faça cópias de segurança (seção 5).

## 8. Desenvolver sem Docker

No próprio Windows, sem prefixos de rota: `powershell -ExecutionPolicy Bypass -File iniciar.ps1` sobe os 7 processos
(3 telas Streamlit, 3 APIs separadas e a Rastreabilidade) em janelas minimizadas. Veja o `README.md`.
