# Servidor da AMATECH Smart Factory (Windows + Docker)

Este guia coloca os quatro sistemas num computador Windows da rede, com **um único IP fixo e uma rota para cada
sistema**. Quem estiver na mesma rede usa as telas pelo navegador, e outros programas leem os dados pelas APIs.

```
navegadores e programas da rede
            │  http://IP/...
            ▼
Servidor Windows (IP fixo) ── Docker
  proxy Caddy (porta 80)
    /                      → página inicial
    /rastreabilidade/      → rastreabilidade   (telas + API, 8000)
    /qualidade/            → qualidade-tela    (8502)
    /qualidade/api/...     → qualidade-api     (5000)
    /manutencao/           → manutencao-tela   (8503)
    /manutencao/api/...    → manutencao-api    (5002)
    /dashboard/            → dashboard-tela    (8501)
    /dashboard/api/...     → dashboard-api     (5003)
```

Cada sistema guarda o banco SQLite num volume do Docker. Entre si, os sistemas se falam pela rede interna do Docker,
pelo nome do serviço (ex.: `http://rastreabilidade:8000`).

Só a porta **80** fica aberta na rede. As portas internas (8000, 5000...) não aparecem fora do Docker.

## 1. Rotas

| Endereço | O que é |
| --- | --- |
| `http://IP/` | Página inicial com os links |
| `http://IP/rastreabilidade/` | Rastreabilidade (login `MAT-0001` / `amatech123`) |
| `http://IP/qualidade/` | Controle da Qualidade |
| `http://IP/manutencao/` | Controle da Manutenção (login `GES-0001` / `123456`) |
| `http://IP/dashboard/` | Dashboard Industrial (login `supervisor` / `super123`) |
| `http://IP/<sistema>/docs` | Documentação interativa da API de cada sistema |

| API | Exemplos | Chave (`X-API-Key`) |
| --- | --- | --- |
| Rastreabilidade | `/rastreabilidade/api/v1/producoes`, `/rastreabilidade/api/v1/passagens?de=&ate=` | criada na tela *Cadastros → Integrações* (ou as de demonstração) |
| Qualidade | `/qualidade/api/ocorrencias?de=AAAA-MM-DD&ate=AAAA-MM-DD` | `QUALIDADE_API_KEY` |
| Manutenção | `/manutencao/api/equipamentos`, `/manutencao/api/manutencao/chamados`, `/manutencao/api/manutencao/indicadores` | `MANUTENCAO_API_KEY` |
| Dashboard | `/dashboard/api/indicadores?de=&ate=&turno=&produto=`, `/dashboard/api/graficos`, `/dashboard/api/paradas-em-andamento` | `DASHBOARD_API_KEY` |

As rotas `/api/status` (e `/rastreabilidade/api/v1/saude`) não pedem chave: servem para testar se o sistema está no ar.

## 2. Preparar o computador (uma vez)

1. **Docker Desktop** para Windows (usa o WSL 2): https://www.docker.com/products/docker-desktop/.
   Em *Settings → General*, marque **Start Docker Desktop when you sign in**.
2. **Git**: https://git-scm.com/download/win.
3. **IP fixo.** O melhor é reservar o IP no roteador (*reserva de DHCP* pelo endereço MAC do servidor). Sem acesso ao
   roteador: *Configurações → Rede e Internet → (adaptador) → Atribuição de IP → Manual*, com IP, máscara, gateway e DNS
   da rede.
4. **Firewall:** liberar a porta 80 (PowerShell como administrador). A rede deve estar como *Privada*.
   ```powershell
   New-NetFirewallRule -DisplayName "AMATECH Smart Factory (porta 80)" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
   ```
5. **Energia:** em *Energia e suspensão*, nunca suspender. O Docker Desktop roda na sessão do usuário: o Windows precisa
   estar com um usuário conectado (configure o logon automático ou deixe a sessão aberta e bloqueada).

## 3. Instalar

```powershell
git clone https://github.com/RadierFalk/amatech-smart-factory.git
cd amatech-smart-factory
copy .env.exemplo .env          # e troque as chaves no .env (o .env não vai para o Git)
docker compose up -d --build    # a primeira vez demora alguns minutos (baixa e monta a imagem)
docker compose ps               # todos devem ficar "running" (as APIs, "healthy")
```

Teste no próprio servidor: http://localhost/. De outro computador: `http://IP-DO-SERVIDOR/`.

Na primeira subida, cada sistema cria o seu banco no volume com os dados de demonstração. Os contêineres usam
`restart: unless-stopped`: voltam sozinhos se travarem e quando o Docker Desktop iniciar com o Windows.

> **Chaves da Rastreabilidade:** ela grava as chaves dos outros sistemas no próprio banco na **primeira** subida. Para
> trocá-las depois, use a tela *Cadastros → Integrações → Gerar nova chave* e atualize o valor correspondente no `.env`
> (`RASTREABILIDADE_CHAVE_QUALIDADE` ou `RASTREABILIDADE_CHAVE_DASHBOARD`); em seguida, `docker compose up -d`.

## 4. Usar as APIs de outro computador

PowerShell:
```powershell
$chave = @{ "X-API-Key" = "amatech-dashboard-demo" }
Invoke-RestMethod "http://192.168.0.50/dashboard/api/indicadores?de=2026-10-01&ate=2026-10-31" -Headers $chave
```

Python:
```python
import requests
r = requests.get("http://192.168.0.50/qualidade/api/ocorrencias", params={"de": "2026-10-01"},
                 headers={"X-API-Key": "amatech-qualidade-demo"}, timeout=5)
print(r.json())
```

## 5. Operação do dia a dia

| Tarefa | Comando (na pasta do repositório) |
| --- | --- |
| Ver o estado | `docker compose ps` |
| Ver os registros de um sistema | `docker compose logs -f qualidade-tela` (ou outro serviço) |
| Reiniciar um sistema | `docker compose restart manutencao-api` |
| Parar tudo / subir de novo | `docker compose down` / `docker compose up -d` |
| **Atualizar** para a versão nova do GitHub | `git pull` e depois `docker compose up -d --build` (os dados ficam nos volumes) |
| **Cópia de segurança** dos bancos | `docker compose cp qualidade-api:/dados ./backup/qualidade` (e o mesmo para `rastreabilidade`, `manutencao-api` e `dashboard-api`) |
| Apagar os dados e recomeçar com a demonstração | `docker compose down -v` (**apaga os volumes**) e `docker compose up -d` |

Serviços: `proxy`, `rastreabilidade`, `qualidade-api`, `qualidade-tela`, `manutencao-api`, `manutencao-tela`,
`dashboard-api`, `dashboard-tela`.

## 6. Problemas comuns

| Sintoma | O que fazer |
| --- | --- |
| `docker compose up` diz que a porta 80 está em uso | Outro programa usa a 80 (IIS, por exemplo). Pare-o, ou troque `"80:80"` por `"8080:80"` no `docker-compose.yml` e acesse `http://IP:8080/` (libere a 8080 no firewall) |
| Abre no servidor, mas não em outro computador | Firewall (passo 2.4), rede *Pública* em vez de *Privada*, ou IP errado (`ipconfig` no servidor) |
| Tela de um sistema fica carregando | `docker compose logs -f <sistema>-tela`; confira se a API dele está *healthy* em `docker compose ps` |
| Sincronização do Dashboard mostra "fora do ar" | O contêiner do outro sistema parou: `docker compose ps` e `docker compose restart <serviço>` |
| Horários com 4 horas de diferença | Os contêineres usam o horário de Manaus (UTC-4); confira o relógio e o fuso do Windows |

## 7. Segurança

- Troque as chaves de demonstração no `.env` antes de liberar o acesso para a turma.
- O acesso é só pela rede local, por HTTP (sem HTTPS). Não exponha a porta 80 para a internet.
- A tela da Qualidade não tem login (o sistema original não tinha); as outras três têm.
- Os bancos ficam nos volumes do Docker, dentro do WSL. Faça cópias de segurança (seção 5).

## 8. Desenvolver sem Docker

No próprio Windows, sem prefixos de rota: `powershell -ExecutionPolicy Bypass -File iniciar.ps1` sobe os 7 processos
(4 telas e 3 APIs separadas, mais a Rastreabilidade) em janelas minimizadas. Veja o `README.md`.
