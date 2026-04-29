[CmdletBinding()]
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $ProjectRoot ".env"

Set-Location $ProjectRoot

function Write-Status {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Detail = ""
    )

    $label = if ($Ok) { "OK" } else { "WARN" }
    $color = if ($Ok) { "Green" } else { "Yellow" }
    $message = "[$label] $Name"
    if ($Detail) {
        $message = "$message - $Detail"
    }
    Write-Host $message -ForegroundColor $color
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

function Invoke-JsonCheck {
    param(
        [string]$Uri,
        [string]$Method = "Get",
        [int]$TimeoutSeconds = 5
    )

    try {
        return Invoke-RestMethod -Uri $Uri -Method $Method -TimeoutSec $TimeoutSeconds
    }
    catch {
        return $null
    }
}

Write-Host "AI Smart Home Demo Status" -ForegroundColor White
Write-Host "Project: $ProjectRoot"
Write-Host ""

$ollamaTags = Invoke-JsonCheck -Uri "http://127.0.0.1:11434/api/tags"
Write-Status -Name "Ollama API" -Ok ([bool]$ollamaTags) -Detail "http://127.0.0.1:11434"

$modelName = Get-EnvValue -Name "OLLAMA_MODEL" -DefaultValue "gemma4:e2b"
if ($ollamaTags) {
    $modelNames = @($ollamaTags.models | ForEach-Object { $_.name })
    Write-Status -Name "Configured Ollama model" -Ok ($modelNames -contains $modelName) -Detail $modelName

    $runningModels = Invoke-JsonCheck -Uri "http://127.0.0.1:11434/api/ps"
    if ($runningModels -and $runningModels.models) {
        $running = ($runningModels.models | ForEach-Object { $_.name }) -join ", "
        Write-Status -Name "Loaded Ollama model" -Ok ($running -match [regex]::Escape($modelName)) -Detail $running
    }
    else {
        Write-Status -Name "Loaded Ollama model" -Ok $false -Detail "No model currently loaded"
    }
}

$health = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/health"
Write-Status -Name "FastAPI health" -Ok ([bool]$health) -Detail "http://127.0.0.1:$Port/health"

$ready = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/ready"
Write-Status -Name "FastAPI ready" -Ok ([bool]$ready) -Detail "http://127.0.0.1:$Port/ready"

$llm = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/health/llm" -TimeoutSeconds 10
if ($llm) {
    $detail = "available=$($llm.available), warmed_up=$($llm.warmed_up), model=$($llm.model)"
    Write-Status -Name "LLM health" -Ok ([bool]$llm.available) -Detail $detail
}
else {
    Write-Status -Name "LLM health" -Ok $false -Detail "No response"
}

$dashboard = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/dashboard/status" -TimeoutSeconds 10
if ($dashboard) {
    Write-Status -Name "Dashboard status" -Ok $true -Detail "demo_mode=$($dashboard.app.demo_mode)"
    if ($dashboard.device) {
        Write-Status -Name "ESP32 status" -Ok ([bool]$dashboard.device.online) -Detail "online=$($dashboard.device.online), last_seen=$($dashboard.device.last_seen_at)"
    }
}
else {
    Write-Status -Name "Dashboard status" -Ok $false -Detail "No response"
}

$voice = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/voice/status" -TimeoutSeconds 10
if ($voice) {
    Write-Status -Name "Voice/TTS status" -Ok ([bool]$voice.tts_enabled) -Detail "provider=$($voice.provider), audio_ready=$($voice.audio_ready)"
}
else {
    Write-Status -Name "Voice/TTS status" -Ok $false -Detail "No response"
}
