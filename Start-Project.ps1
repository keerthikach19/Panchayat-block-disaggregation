param([switch]$Setup, [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if ($Setup) {
        if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
            python -m venv .venv
            if ($LASTEXITCODE -ne 0) { throw 'Python 3.13 environment creation failed.' }
        }
        & '.venv\Scripts\python.exe' -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
        Push-Location frontend
        try {
            $projectNodePath = (Get-Command node -ErrorAction Stop).Source
            $projectNpmCli = Join-Path (Split-Path $projectNodePath) 'node_modules\npm\bin\npm-cli.js'
            if (Test-Path -LiteralPath $projectNpmCli) {
                & $projectNodePath $projectNpmCli ci
                if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
                & $projectNodePath $projectNpmCli run build
            } else {
                & npm.cmd ci
                if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
                & npm.cmd run build
            }
            if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        } finally { Pop-Location }
    }
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe') -or -not (Test-Path -LiteralPath 'frontend\dist\index.html')) {
        throw 'Run .\Start-Project.ps1 -Setup first (Python 3.13 and Node 22 required).'
    }
    Write-Host "Open http://127.0.0.1:$Port — press Ctrl+C to stop."
    & '.venv\Scripts\python.exe' -m uvicorn src.api.main:app --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Server stopped with exit code $LASTEXITCODE. Check whether port $Port is already in use." }
} finally { Pop-Location }
