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

function Resolve-OllamaExe {
    $configured = Get-EnvValue -Name "OLLAMA_EXE" -DefaultValue ""
    $candidates = New-Object System.Collections.Generic.List[string]

    if ($configured) {
        [void]$candidates.Add($configured)
    }
    if ($env:LOCALAPPDATA) {
        [void]$candidates.Add((Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe"))
        [void]$candidates.Add((Join-Path $env:LOCALAPPDATA "Ollama\ollama.exe"))
    }
    if ($env:ProgramFiles) {
        [void]$candidates.Add((Join-Path $env:ProgramFiles "Ollama\ollama.exe"))
    }
    [void]$candidates.Add("ollama")

    foreach ($candidate in $candidates) {
        $candidate = $candidate.Trim()
        if (-not $candidate) {
            continue
        }

        if ($candidate -eq "ollama") {
            $command = Get-Command "ollama" -ErrorAction SilentlyContinue
            if ($command) {
                return $command.Source
            }
            continue
        }

        $expanded = [Environment]::ExpandEnvironmentVariables($candidate)
        if (Test-Path -LiteralPath $expanded -PathType Leaf) {
            return $expanded
        }
    }

    return ""
}

function Resolve-PythonCommand {
    $candidates = @(
        @{
            File = (Join-Path $ProjectRoot ".venv\Scripts\python.exe")
            PrefixArgs = @()
            Label = ".venv"
        },
        @{
            File = (Join-Path $ProjectRoot "venv\Scripts\python.exe")
            PrefixArgs = @()
            Label = "venv"
        },
        @{
            File = "C:\Users\NOTEBOOK\AppData\Local\Programs\Python\Python310\python.exe"
            PrefixArgs = @()
            Label = "Python310"
        },
        @{
            File = "py"
            PrefixArgs = @("-3.11")
            Label = "py -3.11"
        },
        @{
            File = "python"
            PrefixArgs = @()
            Label = "python"
        }
    )

    foreach ($candidate in $candidates) {
        if ($candidate.File -match "\\python\.exe$" -and -not (Test-Path $candidate.File)) {
            continue
        }
        if ($candidate.File -in @("py", "python") -and -not (Get-Command $candidate.File -ErrorAction SilentlyContinue)) {
            continue
        }

        $testArgs = @($candidate.PrefixArgs) + @("-c", "import server.app")
        try {
            $previousErrorActionPreference = $ErrorActionPreference
            $ErrorActionPreference = "SilentlyContinue"
            & $candidate.File @testArgs *> $null
            $exitCode = $LASTEXITCODE
        }
        catch {
            Write-Warn "Skipping Python runtime '$($candidate.Label)' because it failed to start"
            continue
        }
        finally {
            $ErrorActionPreference = $previousErrorActionPreference
        }

        if ($exitCode -eq 0) {
            Write-Ok "Using Python runtime: $($candidate.Label)"
            return @{
                File = $candidate.File
                PrefixArgs = $candidate.PrefixArgs
            }
        }

        Write-Warn "Skipping Python runtime '$($candidate.Label)' because it cannot import server.app"
    }

    throw "No working Python runtime found for this project"
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

    $ollamaExe = Resolve-OllamaExe
    if (-not $ollamaExe) {
        Write-Warn "Ollama executable was not found. Install Ollama or set OLLAMA_EXE in .env."
        return
    }

    $modelsDir = Get-EnvValue -Name "OLLAMA_MODELS" -DefaultValue "D:\Ollama_Models"
    if (-not (Test-Path $modelsDir)) {
        Write-Warn "Ollama model folder was not found: $modelsDir"
    }

    Write-Step "Starting Ollama serve"
    Write-Ok "Ollama executable: $ollamaExe"
    $command = "set `"OLLAMA_MODELS=$modelsDir`" && `"$ollamaExe`" serve"
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $command) -WorkingDirectory $ProjectRoot -WindowStyle Hidden
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

function Get-LanUrls {
    $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -notlike "127.*" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.AddressState -eq "Preferred"
        } |
        Select-Object -ExpandProperty IPAddress

    return @($ips | ForEach-Object { "http://${_}:$Port/" })
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
$lanUrls = Get-LanUrls
if ($lanUrls.Count -gt 0) {
    Write-Host "LAN URL for ESP32/phone: $($lanUrls -join ', ')" -ForegroundColor Green
}
Write-Host "If Voice Node is offline after an IP change, run: .\check_voice_node_network.ps1" -ForegroundColor Yellow
