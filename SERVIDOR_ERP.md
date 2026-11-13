# Servidor do ERP AMATECH (API única + Angular + PostgreSQL)

Este guia publica o **ERP** em produção: Docker **Swarm**, **Traefik** na rede `VandreNet`, imagens no GHCR. O arquivo
é o `docker-compose.yml` da raiz. Ele **substitui** o sistema antigo em Streamlit, que fica em
`docker-compose.legado.yml` (guia [SERVIDOR.md](SERVIDOR.md)) só para voltar atrás.

```
navegador / máquinas da linha
        │  https://<ERP_HOST>/...
        ▼
Traefik (websecure, Let's Encrypt) ── rede VandreNet ──► erp-web (nginx, porta 8080)
                                                            │  /          telas do Angular
                                                            │  /api/...   repassa para a API
                                 rede amatech-erp-interna ─► erp-api (FastAPI, porta 8000)
                                                             │  aplica as migrações ao subir
                                                             ▼
                                                          erp-db (PostgreSQL 17, volume amatech-erp-postgres)
```

Só o `erp-web` fica na `VandreNet`. A API e o banco ficam na rede `amatech-erp-interna`, sem porta publicada. Os dois
processos rodam sem root. O volume do banco (`amatech-erp-postgres`) e a rede interna têm **nome fixo**: os comandos
deste guia valem para qualquer nome de stack. Os exemplos usam a stack **`amatech`**, a mesma do sistema antigo.

## 1. O que precisa existir no servidor

O mesmo do sistema antigo ([SERVIDOR.md](SERVIDOR.md), seção 2): Docker em modo Swarm, a rede overlay `VandreNet`, o
Traefik com o entrypoint `websecure` e o certresolver `letsencryptresolver`. E mais:

| Item | Valor |
| --- | --- |
| DNS | O domínio de `ERP_HOST` apontando para o servidor (o mesmo do sistema antigo já aponta) |
| Imagens | `ghcr.io/radierfalk/amatech-smart-factory-api` e `-web`, publicadas pelo workflow **Imagens do ERP** (`.github/workflows/erp-imagens.yml`) a cada push na `main` que mexa em `backend/` ou `frontend/`, ou pelo botão *Run workflow* |

## 2. Configurar (`.env`)

Copie o `.env.exemplo` para `.env` e preencha a seção **ERP**:

| Variável | Para que serve |
| --- | --- |
| `ERP_HOST` | Domínio do ERP. Em produção, o mesmo do sistema antigo: `amatech.automakad.com.br` |
| `ERP_DB_SENHA` | Senha do PostgreSQL. **Só letras e números** (vai dentro de uma URL) |
| `ERP_JWT_SEGREDO` | Assina os logins. Pelo menos 32 caracteres; trocar derruba as sessões abertas |
| `ERP_CHAVE_MAQUINAS` | `X-API-Key` que as máquinas usam em `/api/ras/maquinas/status` |
| `ERP_SEED_DEMO` | `1` só para testar com os dados de demonstração. **`0` em produção** (os dados vêm da migração) |
| `ERP_IMAGEM_API`, `ERP_IMAGEM_WEB` | Versão das imagens (`latest` ou `sha-xxxxxxx` para fixar uma versão) |

Gerar valores:

```bash
python3 -c "import secrets; print(secrets.token_hex(24))"       # ERP_DB_SENHA
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # ERP_JWT_SEGREDO e ERP_CHAVE_MAQUINAS
```

O deploy recusa subir sem `ERP_HOST`, `ERP_DB_SENHA`, `ERP_JWT_SEGREDO` e `ERP_CHAVE_MAQUINAS`. A API também recusa
segredos de desenvolvimento, os de exemplo (que começam com "troque") e segredo JWT com menos de 32 caracteres.

## 3. Subir em produção (a virada)

Na primeira subida o banco do ERP está vazio, **sem nenhum usuário**: ninguém entra até a migração da seção 4 terminar.
Combine uma janela com os usuários (meia hora basta) e siga na ordem.

```bash
cd amatech-smart-factory && git pull
set -a; . ./.env; set +a                      # o docker stack deploy não lê o .env sozinho

# 1. Cópia de segurança dos volumes antigos, guardada fora do servidor depois.
mkdir -p ~/backup-legado
for v in rastreabilidade qualidade manutencao dashboard portal; do
  docker volume inspect amatech_dados-$v >/dev/null 2>&1 || { echo "sem o volume amatech_dados-$v"; continue; }
  docker run --rm -v amatech_dados-$v:/dados:ro -v ~/backup-legado:/saida alpine \
    tar czf /saida/dados-$v-$(date +%F).tgz -C /dados .
done
ls -lh ~/backup-legado                        # um .tgz por volume

# 2. Troca a stack: --prune remove os serviços antigos (Streamlit) e sobe o ERP. Os volumes amatech_dados-* ficam.
docker stack deploy --prune -c docker-compose.yml amatech
docker stack services amatech                 # erp-db, erp-api e erp-web em 1/1
docker service logs -f amatech_erp-api        # "Aplicando as migrações..." e o uvicorn no ar (Ctrl+C para sair)
```

Teste: `https://<ERP_HOST>/` abre o login e `https://<ERP_HOST>/api/saude` responde `{"api":"ok","banco":"ok"}`.
Em seguida, a migração (seção 4).

**Pelo Portainer:** na stack `amatech`, troque o compose pelo `docker-compose.yml` novo (se a stack vem do Git, use
*Pull and redeploy*), cadastre as variáveis `ERP_*` da seção 2 em *Environment variables* e marque **Prune services**,
para os serviços antigos saírem. Sem o prune, os dois sistemas disputam o mesmo domínio no Traefik.

## 4. Migrar os dados do sistema antigo

O script `scripts/migrar_sqlite.py` (dentro da imagem da API) lê os SQLite antigos e grava no PostgreSQL: usuários
dos cinco sistemas unificados pela matrícula, e os dados da Manutenção, Qualidade, Rastreabilidade e Dashboard. Ele
roda numa transação só (qualquer erro desfaz tudo), pode rodar de novo sem duplicar e tem `--simular`. Regras e
relatório: [HANDOFF_POSTGRES.md](HANDOFF_POSTGRES.md), seção 4.

**Faça num banco vazio** (ERP subido com `ERP_SEED_DEMO=0`). Os serviços antigos já saíram na seção 3, então os
bancos não mudam durante a cópia. Carregue o `.env` antes (`set -a; . ./.env; set +a`).

```bash
# 1. Copie os bancos dos volumes antigos para uma pasta. Os volumes originais não são alterados.
mkdir -p ~/migracao
for v in rastreabilidade qualidade manutencao dashboard portal; do
  docker volume inspect amatech_dados-$v >/dev/null 2>&1 || { echo "sem o volume amatech_dados-$v"; continue; }
  docker run --rm -v amatech_dados-$v:/dados:ro -v ~/migracao:/saida alpine sh -c 'cp /dados/*.db* /saida/ 2>/dev/null; true'
done
ls ~/migracao      # amatech.db, controle_qualidade.db, manutencao.db, banco.db, erp_usuarios.db

# 2. Simule (nada é gravado; o relatório mostra o que vai acontecer, conflitos e pendências).
MIGRAR="docker run --rm --network amatech-erp-interna -v $HOME/migracao:/origem --entrypoint python \
  -e AMATECH_DATABASE_URL=postgresql+psycopg://amatech:${ERP_DB_SENHA}@erp-db:5432/amatech \
  ${ERP_IMAGEM_API} -m scripts.migrar_sqlite \
  --mnt /origem/manutencao.db --qld /origem/controle_qualidade.db --ras /origem/amatech.db \
  --dsh /origem/banco.db --portal /origem/erp_usuarios.db"
$MIGRAR --simular | tee simulacao.txt

# 3. Migre de verdade e guarde o relatório.
$MIGRAR | tee migracao.txt
```

A pasta `~/migracao` é montada **com escrita** de propósito: se algum banco antigo estiver em modo WAL do SQLite,
ele precisa criar arquivos auxiliares para ser lido. É uma cópia; os volumes originais ficam intactos.

Antes de liberar o acesso, confira:

- **Origens ausentes** no relatório: um banco que não estava no volume não é migrado (o resto continua). O
  `erp_usuarios.db` do portal só existe depois que alguém entrou pelo portal; sem ele, ficam de fora só as contas
  criadas na Gestão de Usuários do portal.
- **Pendências** no fim do relatório (decisões que são do dono do projeto, como duas OS ativas na mesma máquina).
- **Possíveis duplicados**: a mesma pessoa com matrículas diferentes em sistemas diferentes (ex.: `MAT-00421` na
  Rastreabilidade e `OP-10234` na Manutenção). Se forem a mesma pessoa, crie um CSV `matricula_antiga,matricula_nova`
  em `~/migracao`, recomece o banco do ERP do zero (fim desta seção) e repita a migração com
  `--equivalencias /origem/equivalencias.csv`.
- **Contas sem login**: senhas antigas em formatos que a API não aceita (PBKDF2 da Rastreabilidade e do Dashboard)
  e contas de serviço. A pessoa entra depois que o Administrador redefinir a senha em *Gestão de usuários*.
- **Senhas das personas** (`ADM-0001`, `GES-0001`, ...) ficam com a senha de demonstração `amatech1234`, que está no
  README. **Redefina-as** em *Gestão de usuários* antes de abrir o sistema para a fábrica.
- O que eram cópias no Dashboard antigo (produção, defeitos e paradas) não é migrado, porque agora vem direto dos
  módulos; o relatório lembra disso.

Para recomeçar o banco do ERP do zero: `docker service scale amatech_erp-api=0 amatech_erp-db=0`,
`docker volume rm amatech-erp-postgres`, `docker service scale amatech_erp-db=1 amatech_erp-api=1` e migre de novo.

## 5. Voltar para o sistema antigo

Se algo der errado na virada, o sistema antigo volta como estava, com os dados dos volumes `amatech_dados-*`
(nada foi alterado neles):

```bash
set -a; . ./.env; set +a                      # precisa das variáveis do sistema antigo (AMATECH_HOST, chaves)
docker stack deploy --prune -c docker-compose.legado.yml amatech
```

O volume do ERP (`amatech-erp-postgres`) continua guardado para a próxima tentativa. Mantenha os volumes
`amatech_dados-*` e o `~/backup-legado` por um tempo depois da virada.

## 6. Operação do dia a dia

| Tarefa | Comando |
| --- | --- |
| Estado | `docker stack services amatech` e `docker stack ps amatech` |
| Registros | `docker service logs -f amatech_erp-api` (ou `_erp-web`, `_erp-db`) |
| **Atualizar** | Depois que o workflow publicar as imagens: `git pull`, carregar o `.env` e repetir o `docker stack deploy -c docker-compose.yml amatech`. A API aplica as migrações novas ao subir. Para fixar uma versão, use `ERP_IMAGEM_API=...:sha-xxxxxxx` |
| Voltar uma versão | `ERP_IMAGEM_API` e `ERP_IMAGEM_WEB` com o `sha-` anterior e `docker stack deploy`. **Atenção:** se a versão nova tinha migração de banco, restaure a cópia de segurança feita antes de atualizar |
| Reiniciar | `docker service update --force amatech_erp-api` |
| **Cópia de segurança** | `docker exec $(docker ps -q -f name=amatech_erp-db) pg_dump -U amatech -Fc amatech > amatech-$(date +%F).dump` |
| Restaurar | Com a API parada (`docker service scale amatech_erp-api=0`): `docker exec -i $(docker ps -q -f name=amatech_erp-db) pg_restore -U amatech -d amatech --clean --if-exists --no-owner < arquivo.dump`, depois `scale ...=1` |
| Parar tudo | `docker stack rm amatech` (o volume `amatech-erp-postgres` continua) |

Faça a cópia de segurança **antes de cada atualização** e guarde-a fora do servidor.

## 7. Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| `invalid interpolation format ... required variable ERP_... is missing a value` no deploy | Carregue o `.env` (`set -a; . ./.env; set +a`) ou cadastre a variável no Portainer |
| O domínio ainda mostra o sistema antigo, ou alterna entre os dois | Os serviços antigos não saíram: repita o deploy com `--prune` (no Portainer, **Prune services**) |
| Ninguém consegue entrar logo depois da subida | Normal antes da migração: o banco novo não tem usuários. Rode a seção 4 |
| `erp-api` reiniciando | `docker service logs amatech_erp-api`. "Defina AMATECH_..." = segredo de exemplo/fraco no `.env`; "PostgreSQL não respondeu" = veja o `erp-db` |
| Login responde 401 para todos | `ERP_JWT_SEGREDO` mudou (as sessões antigas caem: entrar de novo) ou a senha da pessoa precisa ser redefinida |
| Telas abrem mas os dados não carregam (502) | A API ainda está aplicando migrações ou caiu: `docker service ps amatech_erp-api` |
| `network amatech-erp-interna not found` ao migrar | O ERP precisa estar no ar (seção 3) |
| Script de migração recusa: "já tem registros com outros IDs" | O banco não está vazio (ex.: subiu com `ERP_SEED_DEMO=1`). Recomece do zero (fim da seção 4) |
| Máquinas recebem 401 | Elas precisam mandar `X-API-Key` com o valor de `ERP_CHAVE_MAQUINAS` |
| Domínio responde 404 do Traefik | DNS ou `ERP_HOST`, e se o Traefik enxerga a `VandreNet` |

## 8. Ensaiar sem mexer na produção

Ensaie numa máquina que não seja o servidor de produção: o volume e a rede têm nome fixo, e um ensaio no mesmo servidor
usaria o banco de produção. O jeito mais simples é a demonstração (`iniciar-demo.bat` ou `./iniciar-demo.sh`, veja o
README). Para testar as imagens publicadas com este compose, use o `docker compose` comum com um arquivo de ajuste que
troque a rede overlay por bridge e publique o `erp-web` só no loopback:

```yaml
# erp-teste.override.yml
services:
  erp-web:
    ports: ["127.0.0.1:18080:8080"]
networks:
  interna: { driver: bridge }
  VandreNet: { external: true, name: erp-teste-vandrenet }   # crie antes: docker network create erp-teste-vandrenet
```

```bash
docker build -t amatech-erp-api:teste backend && docker build -t amatech-erp-web:teste frontend
ERP_HOST=erp.teste.local ERP_DB_SENHA=senhaDeTeste123 ERP_JWT_SEGREDO=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))") \
ERP_CHAVE_MAQUINAS=chave-maquinas-teste ERP_SEED_DEMO=1 ERP_IMAGEM_API=amatech-erp-api:teste ERP_IMAGEM_WEB=amatech-erp-web:teste \
docker compose -p erpteste -f docker-compose.yml -f erp-teste.override.yml up -d
curl http://127.0.0.1:18080/api/saude
```
