param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$DeviceId = "voice-node-01",
    [switch]$Details
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function Get-PercentText {
    param([double]$Value)
    return ("{0}%" -f [Math]::Round($Value * 100))
}

function Get-JsonUtf8 {
    param([string]$Url)
    $client = New-Object System.Net.WebClient
    $client.Encoding = [System.Text.Encoding]::UTF8
    try {
        return ($client.DownloadString($Url) | ConvertFrom-Json)
    } finally {
        $client.Dispose()
    }
}

function Get-ValueOrDefault {
    param($Value, $Default)
    if ($null -eq $Value) {
        return $Default
    }
    return $Value
}

try {
    $encodedDeviceId = [System.Uri]::EscapeDataString($DeviceId)
    $status = Get-JsonUtf8 "$BaseUrl/voice-node/status?device_id=$encodedDeviceId"
    $config = Get-JsonUtf8 "$BaseUrl/voice-node/config?device_id=$encodedDeviceId"
    $report = Get-JsonUtf8 "$BaseUrl/voice-node/audio/report?device_id=$encodedDeviceId"

    Write-Host "Voice Node: $($status.device_id)"
    Write-Host "Online: $($status.online) | State: $($status.state) | IP: $($status.ip_address)"
    Write-Host "Modes: board_talk=$($status.conversation_mode_enabled) | wake=$($status.wake_mode_enabled) | wake_active=$($status.wake_conversation_active)"
    Write-Host "Heartbeat: $($status.seconds_since_heartbeat) seconds ago"
    Write-Host "Tuning: record=$($config.record_seconds)s | gain=$($config.mic_record_gain) | vad=$($config.vad_enabled) | threshold=$($config.vad_threshold) | silence=$($config.vad_silence_stop_ms)ms"
    Write-Host ""
    Write-Host "Test rounds: $($report.total_items)"
    Write-Host "STT success: $(Get-PercentText $report.stt_success_rate) ($($report.stt_success_count)/$($report.total_items))"
    Write-Host "Blank heard text: $($report.blank_heard_count)"
    if ($null -ne $report.average_similarity) {
        Write-Host "Average STT score: $(Get-PercentText $report.average_similarity) ($($report.high_score_count) high-score rounds, $($report.low_score_count) low-score rounds)"
    } else {
        Write-Host "Average STT score: -"
    }
    $audioQualityOkRate = Get-ValueOrDefault $report.audio_quality_ok_rate 0
    $audioQualityOkCount = Get-ValueOrDefault $report.audio_quality_ok_count 0
    Write-Host "Playback success: $(Get-PercentText $report.playback_success_rate) ($($report.playback_success_count) reported ok)"
    Write-Host "Keep mic open rounds: $($report.keep_mic_open_count)"
    Write-Host "Fallback rounds: $($report.fallback_count)"
    Write-Host "Audio quality OK: $(Get-PercentText $audioQualityOkRate) ($audioQualityOkCount/$($report.total_items))"
    if ($null -ne $report.average_peak_ratio) {
        Write-Host "Average peak: $(Get-PercentText $report.average_peak_ratio)"
    }
    if ($null -ne $report.average_rms_ratio) {
        Write-Host "Average RMS: $(Get-PercentText $report.average_rms_ratio)"
    }
    if ($null -ne $report.average_uploaded_duration_ms) {
        Write-Host ("Average audio duration: {0:N1}s" -f ($report.average_uploaded_duration_ms / 1000))
    }
    Write-Host "Ready for demo: $($report.ready_for_demo)"
    if ($null -ne $report.average_peak_ratio -and $report.average_peak_ratio -ge 0.98) {
        Write-Host "Tuning hint: average peak is near 100%; reduce Mic gain in Web UI or move 20-30 cm from INMP441."
    } elseif ($null -ne $report.average_rms_ratio -and $report.average_rms_ratio -lt 0.02) {
        Write-Host "Tuning hint: audio looks quiet; move closer to INMP441 before increasing Mic gain in Web UI."
    } elseif ($audioQualityOkRate -lt 0.7 -and $report.total_items -ge 5) {
        Write-Host "Tuning hint: audio quality is unstable; check mic direction, distance, and room noise."
    }
    Write-Host ""
    Write-Host "Notes:"
    foreach ($note in $report.notes) {
        Write-Host "- $note"
    }

    if ($Details) {
        $history = Get-JsonUtf8 "$BaseUrl/voice-node/audio/history?device_id=$encodedDeviceId"
        Write-Host ""
        Write-Host "Last rounds:"
        $index = 1
        foreach ($item in $history.items) {
            $scoreText = if ($null -ne $item.stt_similarity) { Get-PercentText $item.stt_similarity } else { "-" }
            $qualityText = if ($item.uploaded_audio_quality) { $item.uploaded_audio_quality } else { "-" }
            $durationText = if ($null -ne $item.uploaded_audio_duration_ms) { "{0:N1}s" -f ($item.uploaded_audio_duration_ms / 1000) } else { "-" }
            $peakText = if ($null -ne $item.uploaded_audio_peak_ratio) { Get-PercentText $item.uploaded_audio_peak_ratio } else { "-" }
            $rmsText = if ($null -ne $item.uploaded_audio_rms_ratio) { Get-PercentText $item.uploaded_audio_rms_ratio } else { "-" }
            Write-Host ("{0}. STT={1} score={2} quality={3} duration={4} peak={5} rms={6} intent={7} source={8} keep_open={9} playback={10}" -f $index, $item.stt_ok, $scoreText, $qualityText, $durationText, $peakText, $rmsText, $item.intent, $item.source, $item.keep_mic_open, $item.playback_ok)
            if ($item.expected_text) {
                Write-Host "   Expected: $($item.expected_text)"
            }
            Write-Host "   Heard: $($item.heard_text)"
            if ($item.reply) {
                Write-Host "   Reply: $($item.reply)"
            }
            if ($item.uploaded_audio_quality_notes -and $item.uploaded_audio_quality_notes.Count -gt 0) {
                Write-Host "   Audio note: $($item.uploaded_audio_quality_notes -join ' / ')"
            }
            $index++
        }
    }
} catch {
    Write-Error "Voice node report check failed: $($_.Exception.Message)"
    exit 1
}
