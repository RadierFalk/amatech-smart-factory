# Sobe os quatro sistemas do ecossistema, cada um numa janela do PowerShell.
# Uso (na raiz do repositório):  powershell -ExecutionPolicy Bypass -File iniciar.ps1
# Antes, uma vez:  python -m venv .venv ; .venv\Scripts\python -m pip install -r requirements.txt
param(
    [string]$Python = (Join-Path $PSScriptRoot ".venv\Scripts\python.exe")
)

if (-not (Test-Path $Python)) {
    Write-Host "Python do ambiente virtual não encontrado em $Python." -ForegroundColor Red
    Write-Host "Crie o ambiente: python -m venv .venv ; .venv\Scripts\python -m pip install -r requirements.txt"
    exit 1
}

# Ordem: os donos dos cadastros primeiro (a Qualidade busca séries e máquinas ao abrir)
$sistemas = @(
    @{ Nome = "Rastreabilidade (8000)"; Pasta = "rastreabilidade"; Comando = "-m uvicorn app.main:app --port 8000" },
    @{ Nome = "Manutencao (8503 / API 5002)"; Pasta = "manutencao"; Comando = "-m streamlit run app.py" },
    @{ Nome = "Qualidade (8502 / API 5000)"; Pasta = "qualidade"; Comando = "-m streamlit run app.py" },
    @{ Nome = "Dashboard (8501)"; Pasta = "dashboard"; Comando = "-m streamlit run app.py" }
)

foreach ($s in $sistemas) {
    $pasta = Join-Path $PSScriptRoot $s.Pasta
    $script = "`$Host.UI.RawUI.WindowTitle = '$($s.Nome)'; Set-Location -LiteralPath '$pasta'; & '$Python' $($s.Comando)"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $script
    Write-Host "Iniciando $($s.Nome)..."
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "Rastreabilidade: http://localhost:8000   Dashboard: http://localhost:8501"
Write-Host "Qualidade:       http://localhost:8502   Manutenção: http://localhost:8503"
