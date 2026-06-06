param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DeviceId = "voice-node-01",
    [int]$HistoryLimit = 5,
    [switch]$Reset,
    [int]$WatchSeconds = 0,
    [int]$IntervalSeconds = 1
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Invoke-Api {
    param(
        [string]$Method,
        [string]$Path,
        [string]$Body = ""
    )
    $client = New-Object System.Net.WebClient
    $client.Encoding = [System.Text.Encoding]::UTF8
    $client.Headers["Content-Type"] = "application/json"
    try {
        if ($Method -eq "GET") {
            $json = $client.DownloadString("$BaseUrl$Path")
        } else {
            $json = $client.UploadString("$BaseUrl$Path", $Method, $Body)
        }
        if ([string]::IsNullOrWhiteSpace($json)) { return $null }
        return $json | ConvertFrom-Json
    } finally {
        $client.Dispose()
    }
}

function Get-ApiJson {
    param([string]$Path)
    return Invoke-Api -Method "GET" -Path $Path
}

function Format-Seconds {
    param($Seconds)
    if ($null -eq $Seconds) { return "-" }
    return "$Seconds sec ago"
}

function Format-Ms {
    param($Milliseconds)
    if ($null -eq $Milliseconds) { return "-" }
    return "$Milliseconds ms"
}

function Get-ActivityHint {
    param($Status, $Audio)
    if (-not $Status.online) { return "offline" }
    if ($Status.state -eq "RECORDING_COMMAND") { return "recording audio now" }
    if ($Status.state -eq "UPLOADING_AUDIO") { return "uploading audio to server" }
    if ($Status.state -eq "WAITING_SERVER_REPLY") { return "waiting for server reply" }
    if ($Status.state -eq "PLAYING_REPLY") { return "playing assistant reply" }
    if ($Status.state -eq "BEEPING") { return "playing record cue" }
    if ($Status.pending_command_count -gt 0) { return "pending command queued" }
    if ($Status.conversation_mode_enabled) { return "continuous conversation mode" }
    if ($Status.wake_mode_enabled) {
        if ($Status.seconds_since_heartbeat -ge 4) {
            return "wake mode; heartbeat delayed, board may be recording/uploading/playing"
        }
        return "wake mode; waiting for wake phrase"
    }
    if ($Audio.has_result -and $Audio.seconds_since_received -le 5) {
        return "fresh audio was processed"
    }
    return "idle/unknown"
}

function Show-Snapshot {
    $status = Get-ApiJson "/voice-node/status?device_id=$DeviceId"
    $config = Get-ApiJson "/voice-node/config?device_id=$DeviceId"
    $audio = Get-ApiJson "/voice-node/audio/status?device_id=$DeviceId"
    $history = Get-ApiJson "/voice-node/audio/history?device_id=$DeviceId&limit=$HistoryLimit"
    $hint = Get-ActivityHint -Status $status -Audio $audio

    Write-Host "Voice Node Wake Debug: $DeviceId" -ForegroundColor Cyan
    Write-Host "Now: $(Get-Date -Format 'HH:mm:ss')"
    Write-Host "Online: $($status.online) | State: $($status.state) | IP: $($status.ip_address)"
    Write-Host "Activity: $hint"
    Write-Host "Wake mode: $($status.wake_mode_enabled) | Conversation: $($status.conversation_mode_enabled) | Wake active: $($status.wake_conversation_active)"
    Write-Host "Heartbeat: $(Format-Seconds $status.seconds_since_heartbeat) | Pending commands: $($status.pending_command_count)"
    Write-Host "Wake word: $($config.wake_word)"
    Write-Host "Mic: gain=$($config.mic_record_gain) vad=$($config.vad_enabled) threshold=$($config.vad_threshold) record=$($config.record_seconds)s"
    Write-Host ""

    if (-not $audio.has_result) {
        Write-Host "Latest audio upload: none after reset/start." -ForegroundColor Yellow
    } else {
        Write-Host "Latest audio upload" -ForegroundColor Cyan
        Write-Host "Received: $(Format-Seconds $audio.seconds_since_received)"
        Write-Host "Server processing: $(Format-Ms $audio.server_processing_ms) | Playback after processing: $(Format-Ms $audio.playback_after_processing_ms)"
        Write-Host "STT ok: $($audio.stt_ok) | Error: $($audio.stt_error)"
        Write-Host "Heard: $($audio.heard_text)"
        Write-Host "Reply marker: $($audio.reply)"
        Write-Host "Audio quality: $($audio.uploaded_audio_quality) | peak=$($audio.uploaded_audio_peak_ratio) rms=$($audio.uploaded_audio_rms_ratio) clip=$($audio.uploaded_audio_clipping_ratio)"
        if ($audio.uploaded_audio_quality_notes.Count -gt 0) {
            Write-Host "Notes: $($audio.uploaded_audio_quality_notes -join '; ')"
        }
        if ($audio.reply -eq "wake detected") {
            Write-Host "Result: wake phrase detected; conversation_start was queued." -ForegroundColor Green
        } elseif ([string]::IsNullOrWhiteSpace($audio.heard_text)) {
            Write-Host "Result: audio reached the server, but STT did not hear clear speech." -ForegroundColor Yellow
        } elseif ($audio.source -eq "voice_control" -and [string]::IsNullOrWhiteSpace($audio.reply)) {
            Write-Host "Result: audio reached the server, but it did not match the wake phrase." -ForegroundColor Yellow
        } else {
            Write-Host "Result: audio was processed." -ForegroundColor Green
        }
    }

    Write-Host ""
    Write-Host "Recent uploads" -ForegroundColor Cyan
    if ($history.items.Count -eq 0) {
        Write-Host "- none"
    }
    foreach ($item in $history.items) {
        if ([string]::IsNullOrWhiteSpace($item.heard_text)) {
            $heard = "-"
        } else {
            $heard = $item.heard_text
        }

        if ([string]::IsNullOrWhiteSpace($item.reply)) {
            $reply = "-"
        } else {
            $reply = $item.reply
        }

        Write-Host "- $(Format-Seconds $item.seconds_since_received) | server=$(Format-Ms $item.server_processing_ms) | playback=$(Format-Ms $item.playback_after_processing_ms) | STT=$($item.stt_ok) | quality=$($item.uploaded_audio_quality) | heard=$heard | reply=$reply"
    }
}

try {
    if ($Reset) {
        $before = Get-ApiJson "/voice-node/status?device_id=$DeviceId"
        if ($before.pending_command_count -gt 0) {
            Write-Host "Reset will clear $($before.pending_command_count) pending command(s)." -ForegroundColor Yellow
        }
        $resetResult = Invoke-Api -Method "DELETE" -Path "/voice-node/audio/history?device_id=$DeviceId"
        Write-Host "Reset debug history: cleared=$($resetResult.cleared), cleared_pending_command_count=$($resetResult.cleared_pending_command_count)" -ForegroundColor Yellow
        $null = Invoke-Api -Method "POST" -Path "/voice-node/commands/wake-listen-start?device_id=$DeviceId"
        Write-Host "Wake listen start queued. Speak the wake phrase now." -ForegroundColor Green
        Write-Host ""
    }

    if ($WatchSeconds -gt 0) {
        $endAt = (Get-Date).AddSeconds($WatchSeconds)
        while ((Get-Date) -lt $endAt) {
            Show-Snapshot
            if ((Get-Date) -lt $endAt) {
                Write-Host ""
                Write-Host "---- watching, next snapshot in $IntervalSeconds sec ----" -ForegroundColor DarkGray
                Write-Host ""
                Start-Sleep -Seconds ([Math]::Max(1, $IntervalSeconds))
            }
        }
    } else {
        Show-Snapshot
    }
} catch {
    Write-Host ("Failed to read Voice Node debug status: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
