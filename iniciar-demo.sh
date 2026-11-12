#!/usr/bin/env sh
# Sobe o ERP AMATECH completo nesta máquina para demonstração (Docker): banco, API e telas, com dados de exemplo.
#
#   ./iniciar-demo.sh           sobe (a primeira vez faz o build: alguns minutos) e abre o navegador
#   ./iniciar-demo.sh parar     para os contêineres (os dados ficam)
#   ./iniciar-demo.sh zerar     apaga tudo, inclusive o banco; a próxima subida recria os dados de exemplo
#   ./iniciar-demo.sh status    mostra os contêineres
#   ./iniciar-demo.sh logs      acompanha os registros (Ctrl+C para sair)
#
#   Variáveis opcionais: DEMO_PORTA (padrão 8080); DEMO_SEM_NAVEGADOR=1 não abre o navegador.
#   Endereço: http://localhost:8080 · contas ADM-0001, GES-0001, OPE-0001, QUA-0001, TEC-2001, ALM-0001 · senha amatech1234
#
#   Docker dentro do WSL (sem Docker Desktop): a porta publicada pelo Docker não chega ao navegador do Windows.
#   Nesse caso o script repassa a porta com o socat só no localhost e fica aberto; feche a janela para encerrar.
set -eu
cd "$(dirname "$0")"

ARQUIVO=docker-compose.demo.yml
PORTA=${DEMO_PORTA:-8080}
ENDERECO="http://localhost:$PORTA"

no_wsl() { grep -qi microsoft /proc/version 2>/dev/null; }

# No WSL o Docker publica numa porta auxiliar e o socat repassa a porta pedida (ver acima).
if no_wsl; then
  DEMO_PORTA_DOCKER=${DEMO_PORTA_DOCKER:-$((PORTA + 10000))}
else
  DEMO_PORTA_DOCKER=$PORTA
fi
export DEMO_PORTA_DOCKER

dc() { docker compose -f "$ARQUIVO" "$@"; }

verificar_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Docker não encontrado. Instale o Docker (Docker Desktop no Windows/macOS) e tente de novo." >&2
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    echo "O Docker está instalado, mas não está rodando. Inicie o Docker e tente de novo." >&2
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "Falta o plugin 'docker compose'. Atualize o Docker e tente de novo." >&2
    exit 1
  fi
}

pronto() {
  url="http://127.0.0.1:$DEMO_PORTA_DOCKER/api/saude"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "$url" 2>/dev/null | grep -q '"banco": *"ok"'
  else
    wget -qO- "$url" 2>/dev/null | grep -q '"banco": *"ok"'
  fi
}

abrir_navegador() {
  [ "${DEMO_SEM_NAVEGADOR:-0}" = "1" ] && return 0
  if no_wsl && command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c start "" "$ENDERECO" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$ENDERECO" >/dev/null 2>&1 || true
  elif command -v open >/dev/null 2>&1; then
    open "$ENDERECO" >/dev/null 2>&1 || true
  fi
}

subir() {
  verificar_docker
  echo "Subindo o ERP AMATECH (a primeira vez faz o build das imagens e demora alguns minutos)..."
  dc up -d --build
  printf "Esperando a API aplicar as migrações e os dados de exemplo"
  for _ in $(seq 1 90); do
    if pronto; then echo " pronto."; break; fi
    printf "."
    sleep 2
  done
  if ! pronto; then
    echo
    echo "A API não respondeu em 3 minutos. Veja os registros com: ./iniciar-demo.sh logs" >&2
    exit 1
  fi

  cat <<FIM

  ERP AMATECH no ar: $ENDERECO

  Contas de demonstração (senha: amatech1234)
    ADM-0001  Administrador          GES-0001  Supervisor / Gestor
    OPE-0001  Operador               QUA-0001  Inspetor de Qualidade
    TEC-2001  Técnico de Manutenção  ALM-0001  Almoxarife

  Parar: ./iniciar-demo.sh parar  ·  apagar os dados: ./iniciar-demo.sh zerar
FIM

  if no_wsl; then
    if ! command -v socat >/dev/null 2>&1; then
      echo
      echo "Docker no WSL: instale o socat para o navegador do Windows alcançar a porta: sudo apt install socat" >&2
      exit 1
    fi
    abrir_navegador
    echo
    echo "  Docker no WSL: deixe esta janela aberta durante a demonstração (Ctrl+C ou fechar encerra o acesso)."
    exec socat TCP-LISTEN:"$PORTA",bind=127.0.0.1,reuseaddr,fork TCP:127.0.0.1:"$DEMO_PORTA_DOCKER"
  fi
  abrir_navegador
}

case "${1:-subir}" in
  subir) subir ;;
  parar) verificar_docker; dc stop; echo "Parado. Os dados ficam guardados para a próxima subida." ;;
  zerar) verificar_docker; dc down -v; echo "Tudo apagado. A próxima subida recria os dados de exemplo." ;;
  status) verificar_docker; dc ps ;;
  logs) verificar_docker; dc logs -f --tail 100 ;;
  *) echo "Uso: $0 [subir|parar|zerar|status|logs]" >&2; exit 2 ;;
esac
