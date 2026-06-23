param(
    [Parameter(Mandatory = $true)]
    [string]$MessageBase64
)

$message = [System.Text.Encoding]::UTF8.GetString(
    [System.Convert]::FromBase64String($MessageBase64)
)

Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.Speak("Reminder. $message")
$speaker.Dispose()

Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show(
    $message,
    "ULTRON Reminder",
    [System.Windows.MessageBoxButton]::OK,
    [System.Windows.MessageBoxImage]::Information
) | Out-Null
