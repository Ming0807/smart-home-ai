param(
    [Parameter(Mandatory = $true)]
    [string]$Port
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$env:IDF_PATH = "C:\Espressif\frameworks\esp-idf-v5.5.2"
$env:IDF_TOOLS_PATH = "C:\Users\NOTEBOOK\.espressif"
$ProjectPath = Split-Path -Parent $MyInvocation.MyCommand.Path

. "$env:IDF_PATH\export.ps1"
Set-Location $ProjectPath
idf.py -p $Port monitor
