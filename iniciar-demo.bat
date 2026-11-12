@echo off
rem Sobe o ERP AMATECH completo nesta maquina para demonstracao (Docker): banco, API e telas, com dados de exemplo.
rem
rem   iniciar-demo.bat           sobe (a primeira vez faz o build: alguns minutos) e abre o navegador
rem   iniciar-demo.bat parar     para os conteineres (os dados ficam)
rem   iniciar-demo.bat zerar     apaga tudo, inclusive o banco; a proxima subida recria os dados de exemplo
rem   iniciar-demo.bat status    mostra os conteineres
rem   iniciar-demo.bat logs      acompanha os registros (Ctrl+C para sair)
rem
rem Variaveis opcionais: DEMO_PORTA (padrao 8080); DEMO_SEM_NAVEGADOR=1 nao abre o navegador.
rem Precisa do Docker Desktop. Sem ele, se o Docker estiver dentro do WSL, chama o iniciar-demo.sh no WSL.
rem Endereco: http://localhost:8080 - contas ADM-0001, GES-0001, OPE-0001, QUA-0001, TEC-2001, ALM-0001 - senha amatech1234
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "ACAO=%~1"
if "%ACAO%"=="" set "ACAO=subir"
if "%DEMO_PORTA%"=="" set "DEMO_PORTA=8080"
set "DEMO_PORTA_DOCKER=%DEMO_PORTA%"
set "ARQUIVO=docker-compose.demo.yml"

where docker >nul 2>nul
if errorlevel 1 goto :wsl

docker info >nul 2>nul
if errorlevel 1 (
  echo O Docker esta instalado, mas nao esta rodando. Abra o Docker Desktop, espere ficar pronto e tente de novo.
  goto :erro
)

if /i "%ACAO%"=="subir" goto :subir
if /i "%ACAO%"=="parar" (docker compose -f %ARQUIVO% stop & echo Parado. Os dados ficam guardados para a proxima subida. & goto :fim)
if /i "%ACAO%"=="zerar" (docker compose -f %ARQUIVO% down -v & echo Tudo apagado. A proxima subida recria os dados de exemplo. & goto :fim)
if /i "%ACAO%"=="status" (docker compose -f %ARQUIVO% ps & goto :fim)
if /i "%ACAO%"=="logs" (docker compose -f %ARQUIVO% logs -f --tail 100 & goto :fim)
echo Uso: iniciar-demo.bat [subir^|parar^|zerar^|status^|logs]
goto :erro

:subir
echo Subindo o ERP AMATECH (a primeira vez faz o build das imagens e demora alguns minutos)...
docker compose -f %ARQUIVO% up -d --build
if errorlevel 1 goto :erro
echo Esperando a API aplicar as migracoes e os dados de exemplo...
for /l %%i in (1,1,90) do (
  curl -fsS http://127.0.0.1:%DEMO_PORTA%/api/saude 2>nul | findstr /r /c:"\"banco\": *\"ok\"" >nul && goto :pronto
  timeout /t 2 /nobreak >nul
)
echo A API nao respondeu em 3 minutos. Veja os registros com: iniciar-demo.bat logs
goto :erro

:pronto
echo.
echo   ERP AMATECH no ar: http://localhost:%DEMO_PORTA%
echo.
echo   Contas de demonstracao (senha: amatech1234)
echo     ADM-0001  Administrador          GES-0001  Supervisor / Gestor
echo     OPE-0001  Operador               QUA-0001  Inspetor de Qualidade
echo     TEC-2001  Tecnico de Manutencao  ALM-0001  Almoxarife
echo.
echo   Parar: iniciar-demo.bat parar  -  apagar os dados: iniciar-demo.bat zerar
if not "%DEMO_SEM_NAVEGADOR%"=="1" start "" "http://localhost:%DEMO_PORTA%"
goto :fim

:wsl
where wsl >nul 2>nul
if errorlevel 1 (
  echo Docker nao encontrado. Instale o Docker Desktop: https://www.docker.com/products/docker-desktop/
  goto :erro
)
echo Docker Desktop nao encontrado; usando o Docker dentro do WSL...
rem "%~dp0." e nao "%~dp0": a barra final escaparia a aspa. WSLENV leva as variaveis DEMO_* para dentro do WSL.
set "WSLENV=DEMO_PORTA:DEMO_SEM_NAVEGADOR:%WSLENV%"
wsl --cd "%~dp0." sh ./iniciar-demo.sh %ACAO%
if errorlevel 1 goto :erro
goto :fim

:erro
echo.
pause
exit /b 1

:fim
endlocal
