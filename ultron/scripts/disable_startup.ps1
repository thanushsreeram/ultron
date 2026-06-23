$ErrorActionPreference = "Stop"

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Remove-ItemProperty -Path $runKey -Name "ULTRON" -ErrorAction SilentlyContinue
Write-Output "ULTRON_STARTUP_DISABLED"
