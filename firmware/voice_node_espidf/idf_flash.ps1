param(
    [Parameter(Mandatory = $true)]
    [string]$Port
)

$ErrorActionPreference = "Stop"

$env:IDF_PATH = "C:\Espressif\frameworks\esp-idf-v5.5.2"
$env:IDF_TOOLS_PATH = "C:\Users\NOTEBOOK\.espressif"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path

. "$env:IDF_PATH\export.ps1"
Set-Location $ProjectPath
idf.py -p $Port flash
