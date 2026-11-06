# Rendered in-game review of L_Manor + L_Manor_Island (editor binary -game, rendering on), camera tour from
# review_island.py, under LOCK GAMETEST (one game test machine-wide, <= 10 min).
#   powershell -NoProfile -ExecutionPolicy Bypass -File Tools\level\review_island.ps1 -Tag t1
param([string]$Tag = "t1", [int]$MaxSec = 540, [int]$Wait0 = 75, [string]$Set = "island")
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$editor = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "$root\GuessWho\GuessWho.uproject"
$locks = "$root\Tools\agent_logs\locks.md"
$out = "$root\Tools\qa\shots\island_$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
function GameTestLocked { $l = Get-Content $locks | Select-String '^(LOCK|UNLOCK) GAMETEST' | Select-Object -Last 1; return ($l -and "$l" -match '^LOCK') }
function BuildLocked { $l = Get-Content $locks | Select-String '^(LOCK|UNLOCK) BUILD' | Select-Object -Last 1; return ($l -and "$l" -match '^LOCK') }
function AssetLocked {
  # an open "LOCK /Game/..." (asset being edited/compiled) younger than 40 min: a game test would make its saves fail
  $state = @{}
  foreach ($m in (Get-Content $locks | Select-String '^(LOCK|UNLOCK) (/Game/\S+) \S+ (\d\d):(\d\d)')) {
    $g = $m.Matches[0].Groups
    $state[$g[2].Value] = @($g[1].Value, [int]$g[3].Value * 60 + [int]$g[4].Value)
  }
  $now = (Get-Date).Hour * 60 + (Get-Date).Minute
  foreach ($k in $state.Keys) {
    $age = ($now - $state[$k][1] + 1440) % 1440
    if ($state[$k][0] -eq 'LOCK' -and $age -lt 40) { return "$k" }
  }
  return $null
}
function ScriptBusy {
  # editor scripts in flight (ue_run / ue_main / ue_py / update scripts) also compile and save assets
  $py = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'ue_run\.py|ue_main\.py|ue_py\.py|update_level\.sh|update_island\.sh' }
  return [bool]$py
}
$deadline = (Get-Date).AddMinutes(150)
$quiet = 0
while ($quiet -lt 2) {      # two consecutive quiet checks 15 s apart
  if ((GameTestLocked) -or (BuildLocked) -or (AssetLocked) -or (ScriptBusy) -or
      (Get-Process -Name 'UnrealGame','GuessWho' -ErrorAction SilentlyContinue)) { $quiet = 0 } else { $quiet++ }
  if ((Get-Date) -gt $deadline) { "gave up waiting for a quiet editor (locks / compiles)"; exit 1 }
  if ($quiet -lt 2) { Start-Sleep -Seconds 15 }
}
Add-Content $locks ("LOCK GAMETEST level " + (Get-Date -Format 'HH:mm') + " - rendered island review (<= 10 min)") -Encoding utf8
$start = Get-Date
try {
  $env:GW_REVIEW_WAIT = "$Wait0"
  $env:GW_REVIEW_SET = $Set
  # -ExecutePythonScript is editor-only; the "py" console command works in -game, but its path must have no spaces
  $pyRun = "$env:TEMP\gw_review_island.py"
  Copy-Item "$root\Tools\level\review_island.py" $pyRun -Force
  $pyRun = $pyRun.Replace('\', '/')
  $a = @("`"$uproject`"", "/Game/GW/Maps/L_Manor", '-game', '-windowed', '-ResX=1600', '-ResY=900', '-ForceRes', '-WinX=0',
         '-WinY=0', '-nosplash', '-unattended', '-NoLiveCoding', '-nosound', '-log', "-abslog=`"$out\game.log`"",
         "-ExecCmds=`"py $pyRun`"")
  $p = Start-Process -FilePath $editor -ArgumentList $a -PassThru
  $done = $p.WaitForExit($MaxSec * 1000)
  if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force; "killed after $MaxSec s" }
} finally {
  Add-Content $locks ("UNLOCK GAMETEST level " + (Get-Date -Format 'HH:mm')) -Encoding utf8
}
Start-Sleep -Seconds 1
$shots = Get-ChildItem "$root\GuessWho\Saved\Screenshots" -Recurse -Filter "island_*.png" | Where-Object { $_.LastWriteTime -gt $start }
foreach ($f in $shots) { Copy-Item $f.FullName "$out\$($f.Name)" }
"copied $($shots.Count) screenshots to $out (exited by itself: $done, $([int]((Get-Date) - $start).TotalSeconds) s)"
foreach ($pat in 'Error', 'GW review', 'Shader', 'Accessed None') { "${pat}: " + (Select-String -Path "$out\game.log" -Pattern $pat -SimpleMatch).Count }
