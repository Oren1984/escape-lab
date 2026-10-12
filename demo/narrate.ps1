# Synthesizes one WAV per narration sentence with the Windows built-in speech engine.
#   pwsh demo/narrate.ps1
# Output: demo/build/voice/<scene>_<n>.wav. No network access, nothing downloaded.
$ErrorActionPreference = 'Stop'
$demo = $PSScriptRoot
$out = Join-Path $demo 'build\voice'
New-Item -ItemType Directory -Force $out | Out-Null
Remove-Item (Join-Path $out '*.wav') -ErrorAction SilentlyContinue

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('Microsoft Zira Desktop')
$synth.Rate = 0
$format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)

$script = Get-Content (Join-Path $demo 'narration.json') -Raw | ConvertFrom-Json
foreach ($scene in $script.scenes) {
    $i = 0
    foreach ($sentence in $scene.sentences) {
        $i++
        $spoken = if ($sentence.say) { $sentence.say } else { $sentence.text }
        $synth.SetOutputToWaveFile((Join-Path $out ("{0}_{1}.wav" -f $scene.id, $i)), $format)
        $synth.Speak($spoken)
    }
}
$synth.SetOutputToNull()
$synth.Dispose()
"{0} sentences written to {1}" -f (Get-ChildItem $out -Filter *.wav).Count, $out
