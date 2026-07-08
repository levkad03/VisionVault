# scripts/dev.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Make sure infra (postgres/redis/qdrant/minio) is up before starting the app
docker compose -f "$root\docker\docker-compose.yml" up -d

$jobs = @()

$jobs += Start-Job -Name "backend" -ScriptBlock {
    Set-Location "$using:root\backend"
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

$jobs += Start-Job -Name "worker" -ScriptBlock {
    Set-Location "$using:root\backend"
    uv run celery -A app.core.celery_app worker --loglevel=info
}

$jobs += Start-Job -Name "frontend" -ScriptBlock {
    Set-Location "$using:root\frontend"
    npm run dev
}

Write-Host "Started backend, worker, frontend as background jobs. Ctrl+C to stop." -ForegroundColor Cyan

try {
    while ($true) {
        foreach ($job in $jobs) {
            Receive-Job -Job $job | ForEach-Object { Write-Host "[$($job.Name)] $_" }
        }
        Start-Sleep -Milliseconds 300
    }
}
finally {
    Write-Host "`nStopping backend, worker, frontend..." -ForegroundColor Cyan
    $jobs | Stop-Job
    $jobs | Remove-Job
    # infra containers are left running intentionally — restarting Postgres/Qdrant/MinIO
    # every time you Ctrl+C the app is slower than just leaving them up between sessions.
    # Run `docker compose -f docker/docker-compose.yml down` yourself when you want them stopped.
}