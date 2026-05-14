$ErrorActionPreference = "Stop"

$IdfPath = "C:\Espressif\frameworks\esp-idf-v5.5.2"
$IdfToolsPath = "C:\Users\NOTEBOOK\.espressif"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExportScript = Join-Path $IdfPath "export.ps1"

if (-not (Test-Path $ExportScript)) {
    throw "ESP-IDF export script not found: $ExportScript"
}

$command = @"
`$env:IDF_PATH = '$IdfPath'
`$env:IDF_TOOLS_PATH = '$IdfToolsPath'
. '$ExportScript'
Set-Location '$ProjectPath'
Write-Host ''
Write-Host 'ESP-IDF shell ready. Useful commands:' -ForegroundColor Cyan
Write-Host '  idf.py menuconfig'
Write-Host '  idf.py build'
Write-Host '  idf.py -p COMx flash monitor'
"@

Start-Process powershell.exe -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $command)
