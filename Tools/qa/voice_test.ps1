# Headless voice test (no GPU, no sound card). A listen server plays one scripted part of s39 VoiceTestTick:
#   A: conversations near the player, E on NPCs, the bar, the fire;  B: a guest shot dead, the blackout, the attack;
#   C: a guest on fire, the kamikaze, the robot, the piano, an explosion   (~4 min of round each)
# Port 7787 (not 7777: the build manager's smoke-test client must never join a voice test).
# Machine rule (coordinator): one game test at a time, 5 min max, posted as LOCK GAMETEST / UNLOCK GAMETEST in
# locks.md, never while a compile holds a /Game asset or a build cooks (Tools\qa\locks_open.py), and withdrawn if
# another agent's GAMETEST was posted in the same moment. Then Tools\qa\voice_log_check.py checks the logs together.
# -Fake adds -GWVoiceFakeBank (test-only lines, imported by `s31_reactions.py fakebank`).
# Usage: powershell -File Tools\qa\voice_test.ps1 [-Parts A,B,C] [-Fake]
param([string[]]$Parts = @('A', 'B', 'C'), [switch]$Fake)
$root = "J:\Projets\Unreal_Projects\Guess Who"
$locks = "$root\Tools\agent_logs\locks.md"
$out = "$root\Tools\qa\voice"
New-Item -ItemType Directory -Force $out | Out-Null
$editor = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "$root\GuessWho\GuessWho.uproject"
$logs = @()
$Parts = @($Parts | ForEach-Object { $_ -split "," } | Where-Object { $_ })   # -Parts A,C through -File arrives as "A,C"

foreach ($part in $Parts) {
  $t0 = Get-Date
  $got = $false
  while (-not $got) {
    if (((Get-Date) - $t0).TotalMinutes -gt 40) { "gave up waiting for the machine"; exit 2 }
    python -I -X utf8 "$root\Tools\qa\locks_open.py" --quiet
    if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 15; continue }
    Add-Content $locks "LOCK GAMETEST voice $(Get-Date -Format HH:mm) (voice test part $part, 5 min max)" -Encoding utf8
    Start-Sleep -Seconds 4
    $others = python -I -X utf8 "$root\Tools\qa\locks_open.py" | Where-Object { $_ -match '^LOCK ' -and $_ -notmatch '^LOCK GAMETEST voice ' }
    if ($others) {
      Add-Content $locks "UNLOCK GAMETEST voice $(Get-Date -Format HH:mm) (withdrawn: another lock came first, nothing run)" -Encoding utf8
      "race with: $others"; Start-Sleep -Seconds 30; continue
    }
    $got = $true
  }
  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $log = "$out\voice_${part}_$stamp.log"
  $a = @("`"$uproject`"", '/Game/GW/Maps/L_Manor?listen?port=7787?Name=Hote', '-game', '-nullrhi', '-nosound', '-unattended', '-nosplash',
         '-NoLiveCoding', '-port=7787', '-GWDev', '-GWName=Hote', "-GWVoiceTest$part", '-log', "-abslog=`"$log`"")
  if ($Fake) { $a += '-GWVoiceFakeBank' }
  $p = Start-Process -FilePath $editor -ArgumentList $a -PassThru -WindowStyle Hidden
  "part $part pid $($p.Id), log $log"
  if (-not $p.WaitForExit(295 * 1000)) { "part ${part}: 5 min reached, stopping it"; Stop-Process -Id $p.Id -Force }
  Add-Content $locks "UNLOCK GAMETEST voice $(Get-Date -Format HH:mm)" -Encoding utf8
  $logs += $log
  "LogScript warnings in part ${part}: $((Select-String -Path $log -Pattern 'LogScript: Warning').Count)"
}
python -I -X utf8 "$root\Tools\qa\voice_log_check.py" @logs --json "$out\voice_$(Get-Date -Format yyyyMMdd_HHmmss).json"
"exit $LASTEXITCODE"
