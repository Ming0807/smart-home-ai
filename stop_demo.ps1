[CmdletBinding()]
param(
    [int]$Port = 8000,
    [switch]$StopOllama
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

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

function Test-UvicornProcess {
    param([object]$Process)

    if (-not $Process -or -not $Process.CommandLine) {
        return $false
    }

    if ($Process.CommandLine -match "uvicorn server\.app:app" -or $Process.CommandLine -match "server\.app:app") {
        return $true
    }

    if ($Process.CommandLine -match "spawn_main\(parent_pid=(\d+)") {
        $parentPid = [int]$Matches[1]
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId = $parentPid" -ErrorAction SilentlyContinue
        if (-not $parent) {
            return $true
        }
        return [bool]($parent.CommandLine -match "uvicorn server\.app:app" -or $parent.CommandLine -match "server\.app:app")
    }

    return $false
}

function Stop-FastApi {
    Write-Step "Stopping FastAPI demo server"

    $stopped = $false
    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($listener.OwningProcess)" -ErrorAction SilentlyContinue
        if (Test-UvicornProcess -Process $process) {
            Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
            $stopped = $true
        }
        elseif ($process) {
            Write-Warn "Port $Port is used by PID $($listener.OwningProcess): $($process.Name). Not stopping it automatically."
        }
    }

    try {
        $uvicornProcesses = Get-CimInstance Win32_Process -ErrorAction Stop |
            Where-Object {
                $_.Name -like "python*" -and (Test-UvicornProcess -Process $_)
            }
    }
    catch {
        $uvicornProcesses = @()
        Write-Warn "Could not scan all Python processes. Continuing with port-based cleanup only."
    }

    foreach ($process in $uvicornProcesses) {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
        $stopped = $true
    }

    if ($stopped) {
        Start-Sleep -Seconds 2
        Write-Ok "FastAPI server stopped"
    }
    else {
        Write-Ok "No FastAPI server process found"
    }
}

function Stop-OllamaServer {
    Write-Step "Stopping Ollama"
    taskkill /f /im "ollama app.exe" 2>$null | Out-Null
    taskkill /f /im "ollama.exe" 2>$null | Out-Null
    Write-Ok "Ollama stop command sent"
}

Write-Host "AI Smart Home Demo Shutdown" -ForegroundColor White
Write-Host "Project: $ProjectRoot"

Stop-FastApi

if ($StopOllama) {
    Stop-OllamaServer
}
else {
    Write-Warn "Ollama left running. Use -StopOllama if you want to close it too."
}

Write-Host ""
Write-Host "Demo shutdown step completed" -ForegroundColor Green
