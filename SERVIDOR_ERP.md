# Servidor do ERP AMATECH (API única + Angular + PostgreSQL)

Este guia publica o **ERP novo** no mesmo servidor da stack antiga: Docker **Swarm**, **Traefik** na rede `VandreNet`,
imagens no GHCR. Ele roda **ao lado** do sistema Streamlit (`docker-compose.yml`, guia [SERVIDOR.md](SERVIDOR.md)),
em outro domínio e com outros volumes, até a virada (seção 7).

```
navegador / máquinas da linha
        │  https://<ERP_HOST>/...
        ▼
Traefik (websecure, Let's Encrypt) ── rede VandreNet ──► erp-web (nginx, porta 8080)
                                                            │  /          telas do Angular
                                                            │  /api/...   repassa para a API
                                       rede interna ──────► erp-api (FastAPI, porta 8000)
                                       da stack              │  aplica as migrações ao subir
                                                             ▼
                                                          erp-db (PostgreSQL 17, volume erp-postgres)
```

Só o `erp-web` fica na `VandreNet`. A API e o banco ficam numa rede própria da stack (`amatech-erp_interna`), sem
porta publicada. Os dois processos rodam sem root.

## 1. O que precisa existir no servidor

O mesmo da stack antiga ([SERVIDOR.md](SERVIDOR.md), seção 2): Docker em modo Swarm, a rede overlay `VandreNet`, o
Traefik com o entrypoint `websecure` e o certresolver `letsencryptresolver`. E mais:

| Item | Valor |
| --- | --- |
| DNS | O domínio de `ERP_HOST` apontando para o servidor |
| Imagens | `ghcr.io/radierfalk/amatech-smart-factory-api` e `-web`, publicadas pelo workflow **Imagens do ERP** (`.github/workflows/erp-imagens.yml`) a cada push na `main` que mexa em `backend/` ou `frontend/`, ou pelo botão *Run workflow* |

## 2. Configurar (`.env`)

Copie o `.env.exemplo` para `.env` e preencha a seção **ERP novo**:

| Variável | Para que serve |
| --- | --- |
| `ERP_HOST` | Domínio do ERP (ex.: `erp.amatech.automakad.com.br`) |
| `ERP_DB_SENHA` | Senha do PostgreSQL. **Só letras e números** (vai dentro de uma URL) |
| `ERP_JWT_SEGREDO` | Assina os logins. Pelo menos 32 caracteres; trocar derruba as sessões abertas |
| `ERP_CHAVE_MAQUINAS` | `X-API-Key` que as máquinas usam em `/api/ras/maquinas/status` |
| `ERP_SEED_DEMO` | `1` só para testar com os dados de demonstração. **`0` para migrar os dados reais** |
| `ERP_IMAGEM_API`, `ERP_IMAGEM_WEB` | Versão das imagens (`latest` ou `sha-xxxxxxx` para fixar uma versão) |

Gerar valores:

```bash
python3 -c "import secrets; print(secrets.token_hex(24))"       # ERP_DB_SENHA
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # ERP_JWT_SEGREDO e ERP_CHAVE_MAQUINAS
```

O deploy recusa subir sem `ERP_HOST`, `ERP_DB_SENHA`, `ERP_JWT_SEGREDO` e `ERP_CHAVE_MAQUINAS`. A API também recusa
segredos de desenvolvimento, os de exemplo (que começam com "troque") e segredo JWT com menos de 32 caracteres.

## 3. Instalar

```bash
cd amatech-smart-factory && git pull
set -a; . ./.env; set +a                          # o docker stack deploy não lê o .env sozinho
docker stack deploy -c docker-compose.erp.yml amatech-erp
docker stack services amatech-erp                 # erp-db, erp-api e erp-web em 1/1
docker service logs -f amatech-erp_erp-api        # "Aplicando as migrações..." e o uvicorn no ar
```

Pelo Portainer: *Stacks → Add stack* com o `docker-compose.erp.yml` e as variáveis da seção 2 em
*Environment variables*. O nome da stack precisa ser **`amatech-erp`** (os comandos deste guia usam esse prefixo).

Teste: `https://<ERP_HOST>/` abre o login e `https://<ERP_HOST>/api/saude` responde `{"api": "ok", "banco": "ok"}`.

Na primeira subida o banco está vazio: ou você migra os dados da stack antiga (seção 4), ou sobe uma vez com
`ERP_SEED_DEMO=1` para ver o sistema com os dados de demonstração (login das personas: senha `amatech1234`).

## 4. Migrar os dados da stack antiga

O script `scripts/migrar_sqlite.py` (dentro da imagem da API) lê os SQLite antigos e grava no PostgreSQL: usuários
dos cinco sistemas unificados pela matrícula, e os dados da Manutenção, Qualidade, Rastreabilidade e Dashboard. Ele
roda numa transação só (qualquer erro desfaz tudo), pode rodar de novo sem duplicar e tem `--simular`. Regras e
relatório: [HANDOFF_POSTGRES.md](HANDOFF_POSTGRES.md), seção 4.

**Faça num banco vazio** (stack nova subida com `ERP_SEED_DEMO=0`). Ensaie quantas vezes quiser antes da virada.
Os comandos abaixo usam `ERP_DB_SENHA` e `ERP_IMAGEM_API`: carregue o `.env` antes (`set -a; . ./.env; set +a`).

```bash
# 1. Pare a stack antiga, para os bancos não mudarem durante a cópia (na virada, ela não volta mais).
docker stack rm amatech                           # os volumes continuam

# 2. Copie os bancos dos volumes antigos para uma pasta. Os volumes originais não são alterados.
mkdir -p ~/migracao
for v in rastreabilidade qualidade manutencao dashboard portal; do
  docker run --rm -v amatech_dados-$v:/dados:ro -v ~/migracao:/saida alpine sh -c 'cp /dados/*.db* /saida/ 2>/dev/null; true'
done
ls ~/migracao      # amatech.db, controle_qualidade.db, manutencao.db, banco.db, erp_usuarios.db

# 3. Simule (nada é gravado; o relatório mostra o que vai acontecer, conflitos e pendências).
MIGRAR="docker run --rm --network amatech-erp_interna -v $HOME/migracao:/origem --entrypoint python \
  -e AMATECH_DATABASE_URL=postgresql+psycopg://amatech:${ERP_DB_SENHA}@erp-db:5432/amatech \
  ${ERP_IMAGEM_API} -m scripts.migrar_sqlite \
  --mnt /origem/manutencao.db --qld /origem/controle_qualidade.db --ras /origem/amatech.db \
  --dsh /origem/banco.db --portal /origem/erp_usuarios.db"
$MIGRAR --simular | tee simulacao.txt

# 4. Migre de verdade e guarde o relatório.
$MIGRAR | tee migracao.txt
```

A pasta `~/migracao` é montada **com escrita** de propósito: se algum banco antigo estiver em modo WAL do SQLite,
ele precisa criar arquivos auxiliares para ser lido. É uma cópia; os volumes originais ficam intactos.

Antes de liberar o acesso, confira:

- **Pendências** no fim do relatório (decisões que são do dono do projeto, como duas OS ativas na mesma máquina).
- **Possíveis duplicados**: a mesma pessoa com matrículas diferentes em sistemas diferentes (ex.: `MAT-00421` na
  Rastreabilidade e `OP-10234` na Manutenção). Se forem a mesma pessoa, crie um CSV `matricula_antiga,matricula_nova`
  em `~/migracao`, apague o banco novo (`docker stack rm amatech-erp && docker volume rm amatech-erp_erp-postgres`,
  suba de novo) e repita a migração com `--equivalencias /origem/equivalencias.csv`.
- **Contas sem login**: senhas antigas em formatos que a API não aceita (PBKDF2 da Rastreabilidade e do Dashboard)
  e contas de serviço. A pessoa entra depois que o Administrador redefinir a senha em *Gestão de usuários*.
- **Senhas das personas** (`ADM-0001`, `GES-0001`, ...) ficam com a senha de demonstração `amatech1234`, que está no
  README. **Redefina-as** em *Gestão de usuários* antes de abrir o sistema para a fábrica.

Para começar de novo do zero: `docker stack rm amatech-erp`, `docker volume rm amatech-erp_erp-postgres` e
`docker stack deploy` outra vez.

## 5. Operação do dia a dia

| Tarefa | Comando |
| --- | --- |
| Estado | `docker stack services amatech-erp` e `docker stack ps amatech-erp` |
| Registros | `docker service logs -f amatech-erp_erp-api` (ou `_erp-web`, `_erp-db`) |
| **Atualizar** | Depois que o workflow publicar as imagens: `git pull`, carregar o `.env` e repetir o `docker stack deploy`. A API aplica as migrações novas ao subir. Para fixar uma versão, use `ERP_IMAGEM_API=...:sha-xxxxxxx` |
| Voltar uma versão | `ERP_IMAGEM_API` e `ERP_IMAGEM_WEB` com o `sha-` anterior e `docker stack deploy`. **Atenção:** se a versão nova tinha migração de banco, restaure a cópia de segurança feita antes de atualizar |
| Reiniciar | `docker service update --force amatech-erp_erp-api` |
| **Cópia de segurança** | `docker exec $(docker ps -q -f name=amatech-erp_erp-db) pg_dump -U amatech -Fc amatech > amatech-$(date +%F).dump` |
| Restaurar | Com a API parada (`docker service scale amatech-erp_erp-api=0`): `docker exec -i $(docker ps -q -f name=amatech-erp_erp-db) pg_restore -U amatech -d amatech --clean --if-exists --no-owner < arquivo.dump`, depois `scale ...=1` |
| Parar tudo | `docker stack rm amatech-erp` (o volume `amatech-erp_erp-postgres` continua) |

Faça a cópia de segurança **antes de cada atualização** e guarde-a fora do servidor.

## 6. Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| `invalid interpolation format ... required variable ERP_... is missing a value` no deploy | Carregue o `.env` (`set -a; . ./.env; set +a`) ou cadastre a variável no Portainer |
| `erp-api` reiniciando | `docker service logs amatech-erp_erp-api`. "Defina AMATECH_..." = segredo de exemplo/fraco no `.env`; "PostgreSQL não respondeu" = veja o `erp-db` |
| Login responde 401 para todos | `ERP_JWT_SEGREDO` mudou (as sessões antigas caem: entrar de novo) ou a senha da pessoa precisa ser redefinida |
| Telas abrem mas os dados não carregam (502) | A API ainda está aplicando migrações ou caiu: `docker service ps amatech-erp_erp-api` |
| `network amatech-erp_interna not found` ao migrar | A stack precisa estar no ar, com o nome `amatech-erp` |
| Script de migração recusa: "já tem registros com outros IDs" | O banco não está vazio (ex.: subiu com `ERP_SEED_DEMO=1`). Recomece do zero (seção 4) |
| Máquinas recebem 401 | Elas precisam mandar `X-API-Key` com o valor de `ERP_CHAVE_MAQUINAS` |
| Domínio responde 404 do Traefik | DNS ou `ERP_HOST`, e se o Traefik enxerga a `VandreNet` |

## 7. A virada (desligar o Streamlit)

1. Ensaie a migração (seção 4) com a stack antiga ainda no ar, só copiando os bancos, e confira o relatório e as telas.
2. No dia: avise os usuários, faça a cópia dos volumes antigos ([SERVIDOR.md](SERVIDOR.md), seção 5), pare a stack
   antiga (`docker stack rm amatech`), apague o banco de ensaio e migre de verdade (seção 4).
3. Redefina as senhas das personas e confira as telas dos cinco módulos.
4. Aponte o domínio antigo para o ERP novo, se for o caso: troque `ERP_HOST` e repita o deploy.
5. Mantenha os volumes `amatech_dados-*` por um tempo como cópia. O que eram cópias no Dashboard antigo
   (produção, defeitos e paradas) não é migrado, porque agora vem direto dos módulos; o relatório lembra disso.
6. Abra o PR da `feature/angular` para a `main`. Depois do merge, a stack antiga e o Streamlit podem sair do repositório.

## 8. Testar a stack sem Swarm

Para conferir as imagens numa máquina sem Swarm (ex.: Docker no WSL), use o `docker compose` comum com um arquivo de
ajuste que troque a rede overlay por bridge e publique o `erp-web` só no loopback:

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
docker compose -p erpteste -f docker-compose.erp.yml -f erp-teste.override.yml up -d
curl http://127.0.0.1:18080/api/saude
```
