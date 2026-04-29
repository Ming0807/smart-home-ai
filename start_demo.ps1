[CmdletBinding()]
param(
    [string]$HostAddress = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$NoServerRestart,
    [switch]$NoOllamaStart,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $ProjectRoot ".env"

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

function Get-EnvValue {
    param(
        [string]$Name,
        [string]$DefaultValue = ""
    )

    if (-not (Test-Path $EnvFile)) {
        return $DefaultValue
    }

    $line = Get-Content -Path $EnvFile |
        Where-Object { $_ -match "^\s*$([regex]::Escape($Name))\s*=" } |
        Select-Object -Last 1

    if (-not $line) {
        return $DefaultValue
    }

    return (($line -replace "^\s*$([regex]::Escape($Name))\s*=\s*", "").Trim('"').Trim("'"))
}

function Resolve-PythonCommand {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return @{
            File = $venvPython
            PrefixArgs = @()
        }
    }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @{
            File = "py"
            PrefixArgs = @("-3.11")
        }
    }

    return @{
        File = "python"
        PrefixArgs = @()
    }
}

function Test-HttpReady {
    param(
        [string]$Uri,
        [int]$TimeoutSeconds = 3
    )

    try {
        Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec $TimeoutSeconds | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-HttpReady {
    param(
        [string]$Uri,
        [int]$TimeoutSeconds = 60,
        [string]$Name = $Uri
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-HttpReady -Uri $Uri -TimeoutSeconds 3) {
            Write-Ok "$Name is ready"
            return $true
        }
        Start-Sleep -Seconds 2
    }

    Write-Warn "$Name did not become ready within $TimeoutSeconds seconds"
    return $false
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

function Stop-ExistingUvicorn {
    Write-Step "Stopping existing FastAPI server on port $Port"

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
        Write-Ok "Old FastAPI process stopped"
    }
    else {
        Write-Ok "No old FastAPI process found"
    }
}

function Start-OllamaIfNeeded {
    if (Test-HttpReady -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSeconds 3) {
        Write-Ok "Ollama is already running"
        return
    }

    $modelsDir = Get-EnvValue -Name "OLLAMA_MODELS" -DefaultValue "D:\Ollama_Models"
    if (-not (Test-Path $modelsDir)) {
        Write-Warn "Ollama model folder was not found: $modelsDir"
    }

    Write-Step "Starting Ollama serve"
    $command = "set `"OLLAMA_MODELS=$modelsDir`" && ollama serve"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", $command) -WorkingDirectory $ProjectRoot -WindowStyle Minimized
    Wait-HttpReady -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSeconds 60 -Name "Ollama" | Out-Null
}

function Check-OllamaModel {
    $modelName = Get-EnvValue -Name "OLLAMA_MODEL" -DefaultValue "gemma4:e2b"

    try {
        $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 5
        $modelNames = @($tags.models | ForEach-Object { $_.name })
        if ($modelNames -contains $modelName) {
            Write-Ok "Ollama model available: $modelName"
        }
        else {
            Write-Warn "Configured model '$modelName' was not found in Ollama tags"
        }
    }
    catch {
        Write-Warn "Could not check Ollama model list"
    }
}

function Start-FastApiServer {
    $python = Resolve-PythonCommand
    $args = @($python.PrefixArgs) + @(
        "-m",
        "uvicorn",
        "server.app:app",
        "--host",
        $HostAddress,
        "--port",
        "$Port"
    )

    Write-Step "Starting FastAPI server without reload"
    Start-Process -FilePath $python.File -ArgumentList $args -WorkingDirectory $ProjectRoot -WindowStyle Minimized
    Wait-HttpReady -Uri "http://127.0.0.1:$Port/health" -TimeoutSeconds 60 -Name "FastAPI" | Out-Null
}

function Warmup-Llm {
    Write-Step "Warming up LLM"
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health/llm/warmup" -Method Post -TimeoutSec 120 | Out-Null
        Write-Ok "LLM warmup request completed"
    }
    catch {
        Write-Warn "LLM warmup did not complete. The first LLM answer may be slower."
    }
}

Write-Host "AI Smart Home Demo Startup" -ForegroundColor White
Write-Host "Project: $ProjectRoot"

if (-not $NoOllamaStart) {
    Start-OllamaIfNeeded
    Check-OllamaModel
}
else {
    Write-Warn "Skipping Ollama startup by request"
}

if (-not $NoServerRestart) {
    Stop-ExistingUvicorn
}
else {
    Write-Warn "Skipping FastAPI restart by request"
}

Start-FastApiServer
Warmup-Llm

Write-Step "Final status"
& (Join-Path $ProjectRoot "check_demo_status.ps1") -Port $Port

if (-not $SkipBrowser) {
    Start-Process "http://127.0.0.1:$Port/"
}

Write-Host ""
Write-Host "Demo is ready: http://127.0.0.1:$Port/" -ForegroundColor Green
