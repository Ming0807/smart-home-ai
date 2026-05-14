$ErrorActionPreference = "Stop"

Get-CimInstance Win32_SerialPort |
    Select-Object DeviceID, Name, Description, Manufacturer |
    Format-Table -AutoSize
