# Sobe o ecossistema ERP completo no Windows, sem Docker (para desenvolver e testar), cada processo numa janela
# minimizada. No servidor, use a stack do Docker Swarm (veja SERVIDOR.md).
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

# Ordem: as APIs e os donos dos cadastros primeiro; depois as telas operacionais e o Portal ERP Central.
$sistemas = @(
    @{ Nome = "Rastreabilidade (8000)"; Pasta = "rastreabilidade"; Comando = "-m uvicorn app.main:app --port 8000" },
    @{ Nome = "Manutencao - API (5002)"; Pasta = "manutencao"; Comando = "-m uvicorn api:app --port 5002" },
    @{ Nome = "Qualidade - API (5000)"; Pasta = "qualidade"; Comando = "-m uvicorn api:app --port 5000" },
    @{ Nome = "Dashboard - API (5003)"; Pasta = "dashboard"; Comando = "-m uvicorn api:app --port 5003" },
    @{ Nome = "Portal ERP Hub (8500)"; Pasta = "portal"; Comando = "-m streamlit run app.py --server.port 8500" },
    @{ Nome = "Manutencao - tela (8503)"; Pasta = "manutencao"; Comando = "-m streamlit run app.py --server.port 8503" },
    @{ Nome = "Qualidade - tela (8502)"; Pasta = "qualidade"; Comando = "-m streamlit run app.py --server.port 8502" },
    @{ Nome = "Dashboard - tela (8501)"; Pasta = "dashboard"; Comando = "-m streamlit run app.py --server.port 8501" }
)

foreach ($s in $sistemas) {
    $pasta = Join-Path $PSScriptRoot $s.Pasta
    $script = "`$Host.UI.RawUI.WindowTitle = '$($s.Nome)'; Set-Location -LiteralPath '$pasta'; & '$Python' $($s.Comando)"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $script -WindowStyle Minimized
    Write-Host "Iniciando $($s.Nome)..."
    Start-Sleep -Seconds 2
}

Write-Host ""
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "🚀 PORTAL ERP AMATECH (Entrada Principal): http://localhost:8500" -ForegroundColor Green
Write-Host "==========================================================================" -ForegroundColor Cyan
Write-Host "Módulos: Rastreabilidade: http://localhost:8000"
Write-Host "         Qualidade:       http://localhost:8502"
Write-Host "         Manutenção:      http://localhost:8503"
Write-Host "         Dashboard Geral: http://localhost:8501"
Write-Host "APIs:    Qualidade http://localhost:5000/docs | Manutenção http://localhost:5002/docs | Dashboard http://localhost:5003/docs"
Write-Host "Para encerrar, feche as janelas minimizadas na barra de tarefas."
