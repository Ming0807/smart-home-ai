[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $ProjectRoot "output\cloudflared.pid"

if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Host "No cloudflared PID file found: $PidFile" -ForegroundColor Yellow
    return
}

$pidText = (Get-Content -LiteralPath $PidFile -Raw).Trim()
if (-not ($pidText -match "^\d+$")) {
    Write-Host "Invalid cloudflared PID file: $pidText" -ForegroundColor Yellow
    return
}

$cloudflaredPid = [int]$pidText
$process = Get-Process -Id $cloudflaredPid -ErrorAction SilentlyContinue
if ($process) {
    Stop-Process -Id $cloudflaredPid -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped Cloudflare tunnel PID $cloudflaredPid" -ForegroundColor Green
}
else {
    Write-Host "Cloudflare tunnel PID $cloudflaredPid is not running" -ForegroundColor Yellow
}

Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
