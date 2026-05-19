[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DeviceId = "voice-node-01",
    [switch]$NoClearHistory,
    [switch]$NoApplyRecommendedTuning,
    [switch]$NoStartConversation
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
    if ($null -ne $Body) {
        $headers["Content-Type"] = "application/json; charset=utf-8"
    }

    if ([string]::IsNullOrWhiteSpace($Body)) {
        return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $headers -TimeoutSec 15
    }

    return Invoke-RestMethod -Uri $Uri -Method $Method -Headers $headers -Body $Body -TimeoutSec 15
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

Write-Host "Voice Node Board Talk Test Prep" -ForegroundColor White
Write-Host "Device: $DeviceId"
Write-Host "Server: $BaseUrl"

Write-Step "Checking Voice Node status"
$status = Invoke-JsonUtf8 "$BaseUrl/voice-node/status?device_id=$encodedDeviceId"
Write-Host "Online: $($status.online) | State: $($status.state) | IP: $($status.ip_address) | Board talk: $($status.conversation_mode_enabled)"
if (-not $status.online) {
    Write-Warning "Voice Node is offline. Check board power, Wi-Fi, and server IP before testing."
}

if (-not $NoApplyRecommendedTuning) {
    Write-Step "Applying recommended board-talk tuning"
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

if (-not $NoStartConversation) {
    Write-Step "Starting board conversation mode"
    $queued = Invoke-JsonUtf8 "$BaseUrl/voice-node/commands/conversation-start?device_id=$encodedDeviceId" -Method "Post"
    Write-Ok "Queued command=$($queued.command.type), pending=$($queued.pending_command_count)"
}

Write-Step "How to test now"
Write-Host "1. Wait for the short cue beep from the board."
Write-Host "2. Speak near INMP441, around 10-20 cm."
Write-Host "3. Try your first Thai sentence."
Write-Host "4. Continue for 5-10 short turns."
Write-Host "5. Include one news command and one LINE-send command if you want to test integrations."
Write-Host "6. Stop by clicking the UI stop button or running:"
$stopCommand = "Invoke-RestMethod -Method Post `"$BaseUrl/voice-node/commands/conversation-stop?device_id=$encodedDeviceId`""
Write-Host "   $stopCommand"
Write-Host ""
Write-Host "After 5-10 rounds, run:"
Write-Host "   .\check_voice_node_report.ps1 -Details"
