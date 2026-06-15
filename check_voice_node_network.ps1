[CmdletBinding()]
param(
    [int]$Port = 8000,
    [string]$DeviceId = "voice-node-01"
)

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SdkconfigPath = Join-Path $ProjectRoot "firmware\voice_node_espidf\sdkconfig"

Set-Location $ProjectRoot

function Get-FirmwareServerUrl {
    if (-not (Test-Path $SdkconfigPath)) {
        return $null
    }

    $line = Get-Content -Path $SdkconfigPath |
        Where-Object { $_ -match '^\s*CONFIG_VOICE_NODE_SERVER_BASE_URL=' } |
        Select-Object -Last 1
    if (-not $line) {
        return $null
    }

    return ($line -replace '^\s*CONFIG_VOICE_NODE_SERVER_BASE_URL=', '').Trim('"')
}

function Get-HostFromUrl {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return $null
    }
    if ($Url -match '^https?://(?<host>[^/:]+)(:\d+)?') {
        return $Matches.host
    }
    return $null
}

function Invoke-JsonCheck {
    param(
        [string]$Uri,
        [int]$TimeoutSeconds = 4
    )

    try {
        return Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec $TimeoutSeconds
    }
    catch {
        return $null
    }
}

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

function Get-PreferredLanIp {
    $configs = @(Get-NetIPConfiguration |
        Where-Object {
            $_.NetAdapter.Status -eq "Up" -and
            $_.IPv4Address -and
            $_.IPv4Address.IPAddress -notlike "127.*" -and
            $_.IPv4Address.IPAddress -notlike "169.254.*"
        })

    $preferred = $configs |
        Sort-Object {
            if ($_.InterfaceAlias -eq "Wi-Fi") { 0 }
            elseif ($_.IPv4DefaultGateway) { 1 }
            elseif ($_.InterfaceAlias -like "vEthernet*") { 3 }
            else { 2 }
        } |
        Select-Object -First 1

    if (-not $preferred) {
        return $null
    }

    return $preferred.IPv4Address.IPAddress
}

$firmwareUrl = Get-FirmwareServerUrl
$firmwareHost = Get-HostFromUrl $firmwareUrl
$localIps = @(Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.AddressState -eq "Preferred"
    } |
    Select-Object InterfaceAlias, IPAddress, PrefixLength, SkipAsSource)
$primaryLanIp = Get-PreferredLanIp

Write-Host "Voice Node Network Check" -ForegroundColor White
Write-Host "Project: $ProjectRoot"
Write-Host ""

if ($firmwareUrl) {
    Write-Status -Name "Firmware server URL in sdkconfig" -Ok $true -Detail $firmwareUrl
}
else {
    Write-Status -Name "Firmware server URL in sdkconfig" -Ok $false -Detail "Not found"
}

Write-Host ""
Write-Host "Current notebook IPv4 addresses:"
if ($localIps.Count -gt 0) {
    $localIps | Format-Table -AutoSize
}
else {
    Write-Host "  No preferred non-loopback IPv4 address found." -ForegroundColor Yellow
}

$health = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/health"
Write-Status -Name "Local FastAPI" -Ok ([bool]$health) -Detail "http://127.0.0.1:$Port/health"

if ($firmwareHost) {
    $hasFirmwareIp = [bool]($localIps | Where-Object { $_.IPAddress -eq $firmwareHost })
    Write-Status -Name "Notebook owns firmware target IP" -Ok $hasFirmwareIp -Detail $firmwareHost

    $firmwareHealth = Invoke-JsonCheck -Uri "http://${firmwareHost}:$Port/health"
    Write-Status -Name "FastAPI reachable on firmware IP" -Ok ([bool]$firmwareHealth) -Detail "http://${firmwareHost}:$Port/health"
}

$encodedDeviceId = [System.Uri]::EscapeDataString($DeviceId)
$voiceNodeStatus = Invoke-JsonCheck -Uri "http://127.0.0.1:$Port/voice-node/status?device_id=$encodedDeviceId"
if ($voiceNodeStatus) {
    $detail = "online=$($voiceNodeStatus.online), state=$($voiceNodeStatus.state), board_ip=$($voiceNodeStatus.ip_address), last_seen=$($voiceNodeStatus.last_seen_at)"
    Write-Status -Name "Voice Node server status" -Ok ([bool]$voiceNodeStatus.online) -Detail $detail
}
else {
    Write-Status -Name "Voice Node server status" -Ok $false -Detail "No response from API"
}

if ($firmwareHost -and -not [bool]($localIps | Where-Object { $_.IPAddress -eq $firmwareHost })) {
    Write-Host ""
    Write-Host "Suggested no-flash rescue command:" -ForegroundColor Cyan
    Write-Host "  Start PowerShell as Administrator, then run:"
    Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$ProjectRoot\fix_voice_node_ip_alias_admin.ps1`" -FirmwareServerIp $firmwareHost"
    Write-Host ""
    Write-Host "Permanent fix if the network subnet changed:" -ForegroundColor Cyan
    if ($primaryLanIp) {
        Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$ProjectRoot\firmware\voice_node_espidf\idf_configure_local.ps1`" -WifiSsid esp32 -WifiPassword 00000000 -ServerUrl http://${primaryLanIp}:$Port -EnableMic -EnableSpeaker"
        Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$ProjectRoot\firmware\voice_node_espidf\idf_build.ps1`""
        Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$ProjectRoot\firmware\voice_node_espidf\idf_flash.ps1`" -Port COM10"
    }
    else {
        Write-Host "  Reconfigure and flash firmware with the current notebook LAN IP."
    }
}
