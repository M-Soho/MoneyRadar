# MoneyRadar Development Startup Script for Windows

Write-Host "🚀 Starting MoneyRadar Development Environment" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Warning: No virtual environment detected" -ForegroundColor Yellow
    Write-Host "   Consider activating with: venv\Scripts\activate" -ForegroundColor Yellow
    Write-Host ""
}

# Check if frontend dependencies are installed
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
    Set-Location frontend
    npm install
    Set-Location ..
    Write-Host "✅ Frontend dependencies installed" -ForegroundColor Green
    Write-Host ""
}

# Initialize database if needed
if (-not (Test-Path "moneyradar.db")) {
    Write-Host "🗄️  Initializing database..." -ForegroundColor Yellow
    python init_db.py
    Write-Host "✅ Database initialized" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host ""
Write-Host "📍 API Server: http://localhost:5000" -ForegroundColor Green
Write-Host "📍 Web UI: http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Start API server in background
Write-Host "Starting API server..." -ForegroundColor Cyan
$apiJob = Start-Job -ScriptBlock { python -m monetization_engine.api.app }

# Give API time to start
Start-Sleep -Seconds 3

# Start frontend dev server in background
Write-Host "Starting Web UI..." -ForegroundColor Cyan
Set-Location frontend
$frontendJob = Start-Job -ScriptBlock { npm run dev }
Set-Location ..

try {
    # Wait for user to press Ctrl+C
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host ""
    Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
    Stop-Job -Job $apiJob, $frontendJob
    Remove-Job -Job $apiJob, $frontendJob
    Write-Host "✅ Services stopped" -ForegroundColor Green
}
