[CmdletBinding()]
param(
    [string]$BackendUrl = "http://127.0.0.1:8000",
    [string]$CloudflaredPath = "",
    [string]$VercelAppUrl = "https://smart-home-ai-lyart.vercel.app/app",
    [switch]$StartDemo,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputDir = Join-Path $ProjectRoot "output"
$OutLog = Join-Path $OutputDir "cloudflared.out.log"
$ErrLog = Join-Path $OutputDir "cloudflared.err.log"
$PidFile = Join-Path $OutputDir "cloudflared.pid"

Set-Location $ProjectRoot

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Resolve-Cloudflared {
    $candidates = New-Object System.Collections.Generic.List[string]

    if ($CloudflaredPath) {
        [void]$candidates.Add($CloudflaredPath)
    }
    [void]$candidates.Add((Join-Path $ProjectRoot "tools\cloudflared.exe"))
    [void]$candidates.Add((Join-Path $ProjectRoot "cloudflared-windows-amd64.exe"))
    [void]$candidates.Add("cloudflared")

    foreach ($candidate in $candidates) {
        if (-not $candidate) {
            continue
        }

        $expanded = [Environment]::ExpandEnvironmentVariables($candidate)
        if ($expanded -eq "cloudflared") {
            $command = Get-Command "cloudflared" -ErrorAction SilentlyContinue
            if ($command) {
                return $command.Source
            }
            continue
        }

        if (Test-Path -LiteralPath $expanded -PathType Leaf) {
            return $expanded
        }
    }

    throw "cloudflared not found. Put cloudflared.exe at tools\cloudflared.exe or install it in PATH."
}

function Test-Backend {
    $healthUrl = "$($BackendUrl.TrimEnd('/'))/health"
    try {
        Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 5 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-TunnelUrl {
    param([int]$TimeoutSeconds = 45)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $pattern = "https://[A-Za-z0-9-]+\.trycloudflare\.com"

    while ((Get-Date) -lt $deadline) {
        $text = ""
        if (Test-Path -LiteralPath $ErrLog) {
            $text += [Environment]::NewLine + (Get-Content -LiteralPath $ErrLog -Raw -ErrorAction SilentlyContinue)
        }
        if (Test-Path -LiteralPath $OutLog) {
            $text += [Environment]::NewLine + (Get-Content -LiteralPath $OutLog -Raw -ErrorAction SilentlyContinue)
        }

        $match = [regex]::Match($text, $pattern)
        if ($match.Success) {
            return $match.Value
        }

        Start-Sleep -Milliseconds 800
    }

    return ""
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

if ($StartDemo) {
    Write-Step "Starting local backend first"
    & (Join-Path $ProjectRoot "start_demo.ps1") -SkipBrowser
}

if (-not (Test-Backend)) {
    Write-Warn "Backend is not ready at $BackendUrl"
    Write-Warn "Run .\start_demo.ps1 first, or rerun this script with -StartDemo"
    exit 1
}

$cloudflared = Resolve-Cloudflared
Write-Step "Starting Cloudflare Quick Tunnel"
Write-Ok "cloudflared: $cloudflared"
Write-Ok "backend: $BackendUrl"

Remove-Item -LiteralPath $OutLog, $ErrLog -Force -ErrorAction SilentlyContinue

$process = Start-Process `
    -FilePath $cloudflared `
    -ArgumentList @("tunnel", "--url", $BackendUrl) `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $PidFile -Value $process.Id -Encoding ASCII

$publicUrl = Wait-TunnelUrl
if (-not $publicUrl) {
    Write-Warn "Tunnel started but the public URL was not found yet."
    Write-Warn "Check: $ErrLog"
    Write-Host "PID: $($process.Id)"
    exit 1
}

$pwaUrl = "$VercelAppUrl?apiBase=$publicUrl"

Write-Host ""
Write-Host "Cloudflare tunnel is ready" -ForegroundColor Green
Write-Host "Backend API: $publicUrl" -ForegroundColor Green
Write-Host "PWA URL:     $pwaUrl" -ForegroundColor Green
Write-Host "PID:         $($process.Id)" -ForegroundColor Green
Write-Host ""
Write-Host "Use this Backend API in the installed PWA Settings:" -ForegroundColor Yellow
Write-Host $publicUrl

if (-not $NoBrowser) {
    Start-Process $pwaUrl
}
