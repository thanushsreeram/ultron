$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $projectRoot "scripts\launch_ultron.ps1"
$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$command = "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$launcher`" voice"

if (-not (Test-Path -LiteralPath $launcher)) {
    throw "ULTRON launcher was not found at $launcher"
}

New-Item -Path $runKey -Force | Out-Null
Set-ItemProperty -Path $runKey -Name "ULTRON" -Value $command -Type String
Write-Output "ULTRON_STARTUP_ENABLED"
