param(
    [Parameter(Mandatory = $true)]
    [string]$WifiSsid,

    [Parameter(Mandatory = $true)]
    [string]$WifiPassword,

    [string]$ServerUrl = "",

    [switch]$EnableMic,

    [switch]$EnableAudioUploadTest,

    [switch]$EnableSpeaker
)

$ErrorActionPreference = "Stop"

$env:IDF_PATH = "C:\Espressif\frameworks\esp-idf-v5.5.2"
$env:IDF_TOOLS_PATH = "C:\Users\NOTEBOOK\.espressif"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$SdkconfigPath = Join-Path $ProjectPath "sdkconfig"

function Escape-SdkconfigString([string]$Value) {
    return $Value.Replace("\", "\\").Replace('"', '\"')
}

function Set-SdkconfigLine([string[]]$Lines, [string]$Key, [string]$Value) {
    $pattern = "^#?\s*$([regex]::Escape($Key))(=.*| is not set)$"
    $replacement = "$Key=$Value"
    $found = $false
    $result = foreach ($line in $Lines) {
        if ($line -match $pattern) {
            $found = $true
            $replacement
        } else {
            $line
        }
    }
    if (-not $found) {
        $result += $replacement
    }
    return $result
}

function Set-SdkconfigDisabled([string[]]$Lines, [string]$Key) {
    $pattern = "^#?\s*$([regex]::Escape($Key))(=.*| is not set)$"
    $replacement = "# $Key is not set"
    $found = $false
    $result = foreach ($line in $Lines) {
        if ($line -match $pattern) {
            $found = $true
            $replacement
        } else {
            $line
        }
    }
    if (-not $found) {
        $result += $replacement
    }
    return $result
}

if ([string]::IsNullOrWhiteSpace($ServerUrl)) {
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -First 1 -ExpandProperty IPAddress
    if ([string]::IsNullOrWhiteSpace($ip)) {
        throw "Could not detect notebook LAN IPv4. Pass -ServerUrl manually."
    }
    $ServerUrl = "http://$ip`:8000"
}

. "$env:IDF_PATH\export.ps1"
Set-Location $ProjectPath

if (-not (Test-Path $SdkconfigPath)) {
    idf.py set-target esp32s3
}

$lines = Get-Content -Encoding UTF8 -Path $SdkconfigPath
$lines = Set-SdkconfigLine $lines "CONFIG_VOICE_NODE_WIFI_SSID" "`"$(Escape-SdkconfigString $WifiSsid)`""
$lines = Set-SdkconfigLine $lines "CONFIG_VOICE_NODE_WIFI_PASSWORD" "`"$(Escape-SdkconfigString $WifiPassword)`""
$lines = Set-SdkconfigLine $lines "CONFIG_VOICE_NODE_SERVER_BASE_URL" "`"$(Escape-SdkconfigString $ServerUrl)`""
$lines = Set-SdkconfigLine $lines "CONFIG_VOICE_NODE_MIC_LOG_INTERVAL_MS" "3000"

if ($EnableMic) {
    $lines = Set-SdkconfigLine $lines "CONFIG_VOICE_NODE_MIC_ENABLED" "y"
} else {
    $lines = Set-SdkconfigDisabled $lines "CONFIG_VOICE_NODE_MIC_ENABLED"
}

if ($EnableAudioUploadTest) {
    $lines = Set-SdkconfigLine $lines "CONFIG_VOICE_NODE_AUDIO_UPLOAD_TEST_ENABLED" "y"
} else {
    $lines = Set-SdkconfigDisabled $lines "CONFIG_VOICE_NODE_AUDIO_UPLOAD_TEST_ENABLED"
}

if ($EnableSpeaker) {
    $lines = Set-SdkconfigLine $lines "CONFIG_VOICE_NODE_SPEAKER_ENABLED" "y"
} else {
    $lines = Set-SdkconfigDisabled $lines "CONFIG_VOICE_NODE_SPEAKER_ENABLED"
}

[System.IO.File]::WriteAllLines(
    $SdkconfigPath,
    [string[]]$lines,
    [System.Text.UTF8Encoding]::new($false))

Write-Host "Configured local sdkconfig:" -ForegroundColor Cyan
Write-Host "  Wi-Fi SSID: $WifiSsid"
Write-Host "  Server URL: $ServerUrl"
Write-Host "  INMP441 mic test: $($EnableMic.IsPresent)"
Write-Host "  Audio upload test: $($EnableAudioUploadTest.IsPresent)"
Write-Host "  MAX98357A speaker test: $($EnableSpeaker.IsPresent)"
Write-Host ""
Write-Host "Next:"
Write-Host "  .\idf_build.ps1"
Write-Host "  .\idf_flash_monitor.ps1 -Port COMx"
