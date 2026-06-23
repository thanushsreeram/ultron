param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$UltronArguments
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$main = Join-Path $projectRoot "main.py"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "ULTRON virtual environment was not found at $python"
    exit 1
}

if (-not (Test-Path -LiteralPath $main)) {
    Write-Error "ULTRON main.py was not found at $main"
    exit 1
}

$launchArguments = @()
if (-not $UltronArguments -or $UltronArguments.Count -eq 0) {
    $launchArguments += "--voice"
}
elseif ($UltronArguments[0] -ieq "voice") {
    $launchArguments += "--voice"
    if ($UltronArguments.Count -gt 1) {
        $launchArguments += $UltronArguments[1..($UltronArguments.Count - 1)]
    }
}
elseif ($UltronArguments[0] -ieq "text") {
    if ($UltronArguments.Count -gt 1) {
        $launchArguments += $UltronArguments[1..($UltronArguments.Count - 1)]
    }
}
else {
    $launchArguments += $UltronArguments
}

Push-Location $projectRoot
try {
    & $python $main @launchArguments
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
