$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$port = 8787
$existing = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1

if ($existing) {
    Write-Host "LLM backend is already listening on http://127.0.0.1:$port (PID $($existing.OwningProcess))."
    exit 0
}

$tempDir = Join-Path $repoRoot "temp"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

$stdout = Join-Path $tempDir "llm-server.out.log"
$stderr = Join-Path $tempDir "llm-server.err.log"

$process = Start-Process `
    -FilePath "node" `
    -ArgumentList @("server/index.mjs") `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

Start-Sleep -Seconds 1

$connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -First 1
if ($connection) {
    Write-Host "LLM backend started on http://127.0.0.1:$port (PID $($process.Id))."
    Write-Host "Logs: $stdout"
    exit 0
}

Write-Error "LLM backend did not start. Check logs: $stderr"
