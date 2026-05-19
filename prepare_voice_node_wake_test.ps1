[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DeviceId = "voice-node-01",
    [switch]$NoClearHistory,
    [switch]$NoApplyRecommendedTuning,
    [switch]$NoStartWake
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Invoke-JsonUtf8 {
    param(
        [string]$Uri,
        [string]$Method = "Get",
        [string]$Body = $null
    )

    $headers = @{ Accept = "application/json" }
    if (-not [string]::IsNullOrWhiteSpace($Body)) {
        $headers["Content-Type"] = "application/json; charset=utf-8"
        return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $headers -Body $Body -TimeoutSec 15
    }

    return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $headers -TimeoutSec 15
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

$encodedDeviceId = [System.Uri]::EscapeDataString($DeviceId)

Write-Host "Voice Node Wake Test Prep" -ForegroundColor White
Write-Host "Device: $DeviceId"
Write-Host "Server: $BaseUrl"

Write-Step "Checking Voice Node status"
$status = Invoke-JsonUtf8 "$BaseUrl/voice-node/status?device_id=$encodedDeviceId"
Write-Host "Online: $($status.online) | State: $($status.state) | IP: $($status.ip_address) | Wake: $($status.wake_mode_enabled) | Active: $($status.wake_conversation_active)"
if (-not $status.online) {
    Write-Warning "Voice Node is offline. Check board power, Wi-Fi, and server IP before testing."
}

if (-not $NoApplyRecommendedTuning) {
    Write-Step "Applying recommended wake/board-talk tuning"
    $payload = @{
        enabled = $true
        record_seconds = 6
        mic_record_gain = 24
        vad_enabled = $true
        vad_threshold = 40
        vad_silence_stop_ms = 900
    } | ConvertTo-Json
    $config = Invoke-JsonUtf8 "$BaseUrl/voice-node/config?device_id=$encodedDeviceId" -Method "Post" -Body $payload
    Write-Ok "Tuning: record=$($config.record_seconds)s gain=$($config.mic_record_gain) vad=$($config.vad_enabled) threshold=$($config.vad_threshold) silence=$($config.vad_silence_stop_ms)ms"
}

if (-not $NoClearHistory) {
    Write-Step "Clearing old Voice Node history and pending test commands"
    $clear = Invoke-JsonUtf8 "$BaseUrl/voice-node/audio/history?device_id=$encodedDeviceId" -Method "Delete"
    Write-Ok "Cleared=$($clear.cleared), cleared_pending_command_count=$($clear.cleared_pending_command_count)"
}

if (-not $NoStartWake) {
    Write-Step "Starting board wake listening mode"
    $queued = Invoke-JsonUtf8 "$BaseUrl/voice-node/commands/wake-listen-start?device_id=$encodedDeviceId" -Method "Post"
    Write-Ok "Queued command=$($queued.command.type), pending=$($queued.pending_command_count)"
}

Write-Step "How to test now"
Write-Host "1. The board listens silently using board-side VAD windows."
Write-Host "2. Say the Thai wake phrase: sawatdee nong fah."
Write-Host "3. After the assistant replies, continue without the wake phrase."
Write-Host "4. Say a sleep phrase when done, or click Stop Wake in the UI."
Write-Host "5. Run this after 5-10 turns:"
Write-Host "   .\check_voice_node_report.ps1 -Details"
