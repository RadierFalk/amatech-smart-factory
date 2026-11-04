# Inicia o ERP Unificado AMATECH em uma única porta (8501) e única sessão.
# Todos os 5 módulos (Rastreabilidade, Qualidade, Manutenção, Dashboard e Gestão de Usuários)
# rodam de forma integrada no mesmo sistema.
#
# Uso:  .\iniciar.ps1

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz

$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Criando ambiente virtual (.venv)..." -ForegroundColor Cyan
    python -m venv .venv
    & $python -m pip install --upgrade pip
    & $python -m pip install -r requirements.txt
}

$env:AMATECH_INTEGRACAO_LOCAL = "1"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  ERP AMATECH (Aplicacao Unificada Modular) — Porta 8501" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  URL Unica:  http://localhost:8501"
Write-Host "  Modulos Integrados:"
Write-Host "    1. Rastreabilidade e Materiais (RAS)"
Write-Host "    2. Controle da Qualidade e Defeitos (QLD)"
Write-Host "    3. Gestao da Manutencao de Ativos (MNT)"
Write-Host "    4. Dashboard Industrial e Metas (DSH)"
Write-Host "    5. Gestao de Usuarios e Acessos (USR)"
Write-Host ""
Write-Host "  Contas de Demonstracao (Senha unica: amatech1234):"
Write-Host "    - ADM-0001 (Administrador):       5 modulos (RAS, QLD, MNT, DSH, USR)"
Write-Host "    - GES-0001 (Supervisor / Gestor): 4 modulos (RAS, QLD, MNT, DSH)"
Write-Host "    - OPE-0001 (Operador):            4 modulos (RAS, QLD, MNT, DSH)"
Write-Host "    - QUA-0001 (Inspetor Qualidade):  3 modulos (RAS, QLD, DSH)"
Write-Host "    - TEC-2001 (Tecnico Manutencao):  2 modulos (MNT, DSH)"
Write-Host "    - ALM-0001 (Almoxarife):          2 modulos (RAS, QLD)"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

& $python -m streamlit run app.py --server.port 8501
