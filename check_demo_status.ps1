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

function Get-VoiceNodeFirmwareServerUrl {
    $sdkconfigPath = Join-Path $ProjectRoot "firmware\voice_node_espidf\sdkconfig"
    if (-not (Test-Path $sdkconfigPath)) {
        return ""
    }

    $line = Get-Content -Path $sdkconfigPath |
        Where-Object { $_ -match '^\s*CONFIG_VOICE_NODE_SERVER_BASE_URL=' } |
        Select-Object -Last 1
    if (-not $line) {
        return ""
    }

    return ($line -replace '^\s*CONFIG_VOICE_NODE_SERVER_BASE_URL=', '').Trim('"')
}

function Get-UrlHost {
    param([string]$Url)
    if ($Url -match '^https?://(?<host>[^/:]+)(:\d+)?') {
        return $Matches.host
    }
    return ""
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

$lanIps = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.AddressState -eq "Preferred"
    } |
    Select-Object -ExpandProperty IPAddress)
if ($lanIps.Count -gt 0) {
    Write-Status -Name "Notebook LAN URL(s)" -Ok $true -Detail (($lanIps | ForEach-Object { "http://${_}:$Port" }) -join ", ")
}

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

$voiceNodeStatus = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/voice-node/status?device_id=voice-node-01" -TimeoutSeconds 10
if ($voiceNodeStatus) {
    $detail = "online=$($voiceNodeStatus.online), state=$($voiceNodeStatus.state), board_talk=$($voiceNodeStatus.conversation_mode_enabled), ip=$($voiceNodeStatus.ip_address)"
    Write-Status -Name "Voice Node status" -Ok ([bool]$voiceNodeStatus.online) -Detail $detail
    if (-not $voiceNodeStatus.online) {
        $firmwareUrl = Get-VoiceNodeFirmwareServerUrl
        $firmwareHost = Get-UrlHost $firmwareUrl
        if ($firmwareUrl) {
            $ownsFirmwareHost = [bool]($lanIps | Where-Object { $_ -eq $firmwareHost })
            Write-Status -Name "Voice Node firmware target" -Ok $ownsFirmwareHost -Detail $firmwareUrl
            if (-not $ownsFirmwareHost -and $firmwareHost) {
                Write-Status -Name "Voice Node IP hint" -Ok $false -Detail "Run .\check_voice_node_network.ps1"
            }
        }
    }
}
else {
    Write-Status -Name "Voice Node status" -Ok $false -Detail "No response"
}

$voiceNodeReport = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/voice-node/audio/report?device_id=voice-node-01" -TimeoutSeconds 10
if ($voiceNodeReport) {
    $detail = "rounds=$($voiceNodeReport.total_items), stt=$([Math]::Round($voiceNodeReport.stt_success_rate * 100))%, playback=$([Math]::Round($voiceNodeReport.playback_success_rate * 100))%, blank=$($voiceNodeReport.blank_heard_count), fallback=$($voiceNodeReport.fallback_count)"
    Write-Status -Name "Voice Node report" -Ok ([bool]$voiceNodeReport.ready_for_demo) -Detail $detail
}
else {
    Write-Status -Name "Voice Node report" -Ok $false -Detail "No response"
}
