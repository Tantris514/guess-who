# Automated QA run: the headless dev test (-GWDevTest: menu, rounds, test round, piano, every event...) under the
# machine-wide GAMETEST lock, then Tools\qa\qa_check.py grades the log (errors + expected features) and, when the voice
# director logs "GW: VO" lines, Tools\qa\voice_log_check.py checks the voices. Reports: Tools\qa\reports\qa_<time>.md.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File Tools\qa\qa_suite.ps1 [-Seconds 260]
param([int]$Seconds = 400)   # the -GWDevTest script ends at step 160 (shop block), ~2 s per step
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$locks = "$root\Tools\agent_logs\locks.md"
$stamp = Get-Date -Format 'yyyyMMdd-HHmm'
$dir = "$root\Tools\qa\reports"
New-Item -ItemType Directory -Force $dir | Out-Null
$log = "$dir\qa_$stamp.log"
function LastLine($word) { (Get-Content $locks -Tail 60 | Select-String $word | Select-Object -Last 1) }
# one game test at a time on the machine, and never during a build
$deadline = (Get-Date).AddMinutes(40)
function AssetLocksOpen {
    # an open LOCK on a /Game asset = someone is compiling; a game test now would make their saves fail (Error 32)
    $state = @{}
    foreach ($l in (Get-Content $locks -Tail 200)) {
        if ($l -match '^(UN)?LOCK (/Game/\S+) (\S+)') { $state[$Matches[2] + ' ' + $Matches[3]] = ($Matches[1] -ne 'UN') }
    }
    return ($state.Values | Where-Object { $_ }).Count -gt 0
}
while (((LastLine 'GAMETEST') -match '^LOCK GAMETEST') -or ((LastLine ' BUILD ') -match '^LOCK BUILD') -or (AssetLocksOpen)) {
    if ((Get-Date) -gt $deadline) { "gave up waiting for GAMETEST/BUILD lock"; exit 2 }
    Start-Sleep -Seconds 20
}
Add-Content $locks ("LOCK GAMETEST coordinator-qa " + (Get-Date -Format 'HH:mm')) -Encoding utf8
try {
    $exe = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
    $argList = @("`"$root\GuessWho\GuessWho.uproject`"", '/Game/GW/Maps/L_Manor?listen?Name=Hote', '-game', '-nullrhi', '-nosound',
        '-unattended', '-nosplash', '-NoLiveCoding', '-GWDev', '-GWDevTest', '-GWName=Hote', '-log', "-abslog=`"$log`"",
        '-port=7791')  # not 7777: the Build Manager's packaged smoke test joins 127.0.0.1:7777
    $p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru
    if (-not $p.WaitForExit($Seconds * 1000)) { Stop-Process -Id $p.Id -Force }
} finally {
    Add-Content $locks ("UNLOCK GAMETEST coordinator-qa " + (Get-Date -Format 'HH:mm')) -Encoding utf8
}
Start-Sleep -Seconds 2
python -I -X utf8 "$root\Tools\qa\qa_check.py" $log "$dir\qa_$stamp.md"
$rc = $LASTEXITCODE
if (Select-String -Path $log -Pattern 'GW: VOX' -Quiet) {
    python -I -X utf8 "$root\Tools\qa\voice_log_check.py" $log | Out-File -Append -Encoding utf8 "$dir\qa_$stamp.md"
}
"report: $dir\qa_$stamp.md (exit $rc)"
exit $rc
