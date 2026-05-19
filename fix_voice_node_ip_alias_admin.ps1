param(
    [string]$InterfaceAlias = "",
    [string]$FirmwareServerIp = "",
    [int]$PrefixLength = 24,
    [switch]$AllKnownFirmwareIps
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SdkconfigPath = Join-Path $ProjectRoot "firmware\voice_node_espidf\sdkconfig"

function Get-FirmwareServerIpFromSdkconfig {
    if (-not (Test-Path $SdkconfigPath)) {
        return $null
    }

    $line = Get-Content -Path $SdkconfigPath |
        Where-Object { $_ -match '^\s*CONFIG_VOICE_NODE_SERVER_BASE_URL=' } |
        Select-Object -Last 1
    if (-not $line) {
        return $null
    }

    $url = ($line -replace '^\s*CONFIG_VOICE_NODE_SERVER_BASE_URL=', '').Trim('"')
    if ($url -match '^https?://(?<host>\d{1,3}(\.\d{1,3}){3})(:\d+)?') {
        return $Matches.host
    }

    return $null
}

function Get-PreferredInterfaceAlias {
    $candidates = Get-NetIPConfiguration |
        Where-Object {
            $_.NetAdapter.Status -eq "Up" -and
            $_.IPv4Address -and
            $_.IPv4Address.IPAddress -notlike "127.*" -and
            $_.IPv4Address.IPAddress -notlike "169.254.*"
        } |
        Sort-Object {
            if ($_.InterfaceAlias -eq "Wi-Fi") { 0 } else { 1 }
        }

    $candidate = $candidates | Select-Object -First 1
    if (-not $candidate) {
        throw "No active IPv4 network adapter was found."
    }

    return $candidate.InterfaceAlias
}

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    $hintIp = $FirmwareServerIp
    if ([string]::IsNullOrWhiteSpace($hintIp)) {
        $hintIp = Get-FirmwareServerIpFromSdkconfig
    }
    $hintArgs = if ([string]::IsNullOrWhiteSpace($hintIp)) { "" } else { " -FirmwareServerIp $hintIp" }
    Write-Host "This script must run in an Administrator PowerShell window." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Open PowerShell as Administrator, then run:"
    Write-Host "  powershell -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"$hintArgs"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($InterfaceAlias)) {
    $InterfaceAlias = Get-PreferredInterfaceAlias
}

$targetIps = @()
if (-not [string]::IsNullOrWhiteSpace($FirmwareServerIp)) {
    $targetIps += $FirmwareServerIp.Trim()
}
else {
    $sdkconfigIp = Get-FirmwareServerIpFromSdkconfig
    if (-not [string]::IsNullOrWhiteSpace($sdkconfigIp)) {
        $targetIps += $sdkconfigIp
    }
}

if ($AllKnownFirmwareIps) {
    $targetIps += @(
        "192.168.183.114",
        "192.168.160.114",
        "192.168.115.114",
        "192.168.16.114"
    )
}

$targetIps = $targetIps |
    Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' } |
    Select-Object -Unique

if (-not $targetIps) {
    throw "No firmware server IP was supplied or found in $SdkconfigPath."
}

Write-Host "Voice Node IP alias rescue" -ForegroundColor White
Write-Host "Interface: $InterfaceAlias"
Write-Host "Target firmware IP(s): $($targetIps -join ', ')"
Write-Host ""

foreach ($targetIp in $targetIps) {
    $existing = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias $InterfaceAlias -ErrorAction Stop |
        Where-Object { $_.IPAddress -eq $targetIp }

    if ($existing) {
        Write-Host "IP alias already exists: $targetIp on $InterfaceAlias" -ForegroundColor Green
        continue
    }

    New-NetIPAddress `
        -InterfaceAlias $InterfaceAlias `
        -IPAddress $targetIp `
        -PrefixLength $PrefixLength `
        -SkipAsSource $true `
        -ErrorAction Stop | Out-Null
    Write-Host "Added IP alias: $targetIp on $InterfaceAlias" -ForegroundColor Green
}

Write-Host ""
Write-Host "Current IPv4 addresses on ${InterfaceAlias}:"
Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias $InterfaceAlias |
    Select-Object IPAddress, PrefixLength, SkipAsSource |
    Format-Table -AutoSize
