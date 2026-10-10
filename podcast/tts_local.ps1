# Offline synthesis with the Hebrew voice installed in Windows (OneCore, he-IL).
# Called by build_local.py. Kept ASCII-only: Windows PowerShell 5.1 reads .ps1 files as ANSI.
# Input: a UTF-8 jobs file, one line per clip:  <wav file to create><TAB><text>
param([Parameter(Mandatory=$true)][string]$Jobs)

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType=WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]

function Await($op, $type) {
    $task = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    $task.Result
}

$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices |
    Where-Object { $_.Language -eq 'he-IL' } | Select-Object -First 1
if (-not $voice) { Write-Output "no he-IL voice installed"; exit 3 }
$synth.Voice = $voice
Write-Output ("voice: " + $voice.DisplayName)

$n = 0
foreach ($line in [IO.File]::ReadAllLines($Jobs, [Text.Encoding]::UTF8)) {
    if (-not $line.Trim()) { continue }
    $parts = $line.Split("`t", 2)
    $out = $parts[0]; $text = $parts[1]
    if (Test-Path -LiteralPath $out) { continue }
    $stream = Await ($synth.SynthesizeTextToStreamAsync($text)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
    $size = [uint32]$stream.Size
    $reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
    $null = Await ($reader.LoadAsync($size)) ([uint32])
    $bytes = New-Object byte[] $size
    $reader.ReadBytes($bytes)
    [IO.File]::WriteAllBytes($out, $bytes)
    $reader.Dispose(); $stream.Dispose()
    $n++
}
Write-Output ("done: " + $n)
