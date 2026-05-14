param(
    [string]$InterfaceAlias = "Wi-Fi",
    [string]$FirmwareServerIp = "192.168.160.114",
    [int]$PrefixLength = 24
)

$ErrorActionPreference = "Stop"

$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Please run PowerShell as Administrator, then run this script again."
}

$existing = Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias $InterfaceAlias -ErrorAction Stop |
    Where-Object { $_.IPAddress -eq $FirmwareServerIp }

if ($existing) {
    Write-Host "IP alias already exists: $FirmwareServerIp on $InterfaceAlias" -ForegroundColor Green
} else {
    New-NetIPAddress `
        -InterfaceAlias $InterfaceAlias `
        -IPAddress $FirmwareServerIp `
        -PrefixLength $PrefixLength `
        -SkipAsSource $true `
        -ErrorAction Stop | Out-Null
    Write-Host "Added IP alias: $FirmwareServerIp on $InterfaceAlias" -ForegroundColor Green
}

Write-Host ""
Write-Host "Current IPv4 addresses on ${InterfaceAlias}:"
Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias $InterfaceAlias |
    Select-Object IPAddress, PrefixLength, SkipAsSource |
    Format-Table -AutoSize
