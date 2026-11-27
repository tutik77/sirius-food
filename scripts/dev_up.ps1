param([switch]$Stop)

$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"

Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "uvicorn app.main|celery -A app.core.celery_app" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
if ($Stop) { return }

New-Item -ItemType Directory -Force logs | Out-Null
docker compose up -d db redis

$processes = @{
    api    = @("-m", "uvicorn", "app.main:app", "--port", "8000")
    worker = @("-m", "celery", "-A", "app.core.celery_app", "worker", "-Q", "default", "--pool=threads", "--concurrency=4", "--loglevel=info")
    beat   = @("-m", "celery", "-A", "app.core.celery_app", "beat", "--loglevel=info", "--schedule", "logs/celerybeat-schedule")
    flower = @("-m", "celery", "-A", "app.core.celery_app", "flower", "--port=5555")
}
foreach ($name in $processes.Keys) {
    Start-Process $py -ArgumentList $processes[$name] -WindowStyle Hidden `
        -RedirectStandardOutput "logs\$name.out.log" -RedirectStandardError "logs\$name.log"
}
Write-Output "api :8000, flower :5555, logs: logs\"
