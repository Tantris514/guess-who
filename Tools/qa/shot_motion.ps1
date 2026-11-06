# Motion QA capture: listen server on L_Manor with -GWLineup -GWMotion (BP_GW_Showcase motion mode, s28_motion_qa.py).
# Every outfit is worn by a walking NPC and shot 6x from the side and 6x from the front; the game quits by itself.
# Usage: powershell -File shot_motion.ps1 [-Tag motion] [-ResX 1280] [-ResY 720]
# -Packaged runs Build\Windows\GuessWho.exe instead of the editor in -game (cooked materials and shaders, as shipped).
param([string]$Tag = "motion", [int]$ResX = 1280, [int]$ResY = 720, [int]$Seconds = 240, [switch]$Packaged)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$proj = "J:\Projets\Unreal_Projects\Guess Who\GuessWho"
$out = "J:\Projets\Unreal_Projects\Guess Who\Tools\qa\motion\$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
$start = Get-Date
$sargs = @("/Game/GW/Maps/L_Manor?listen?Name=Hote", '-windowed', "-ResX=$ResX", "-ResY=$ResY", '-ForceRes',
           '-nosplash', '-unattended', '-nosound', '-GWLineup', '-GWMotion', '-GWName=Hote', '-log', "-abslog=`"$out\server.log`"")
if ($Packaged) {
  $exe = "J:\Projets\Unreal_Projects\Guess Who\Build\Windows\GuessWho.exe"
  $proj = "J:\Projets\Unreal_Projects\Guess Who\Build\Windows\GuessWho"
} else {
  $exe = $editor
  $sargs = @("`"$uproject`"") + $sargs + @('-game', '-NoLiveCoding')
}
$s = Start-Process -FilePath $exe -ArgumentList $sargs -PassThru
$null = $s.WaitForExit($Seconds * 1000)
if (-not $s.HasExited) { Stop-Process -Id $s.Id -Force; "timed out after $Seconds s" }
Start-Sleep -Seconds 1
$shots = Get-ChildItem "$proj\Saved\Screenshots" -Recurse -Filter *.png | Where-Object { $_.LastWriteTime -gt $start }
# A "Shot" issued while the previous one is still pending replaces it (a hitch longer than the 0.15 s timer), so the
# files are matched to labels through the log: each 'Tracing Screenshot "ScreenShotNNNNN"' takes the last shot label.
$byFile = @{}; $pending = $null; $labelled = 0
foreach ($line in Get-Content "$out\server.log") {
  if ($line -match 'GW mq shot k=(\d+) v=(\w+) f=(\d+)') {
    $pending = "k{0:D2}_{1}_f{2:D2}" -f [int]$Matches[1], $Matches[2], [int]$Matches[3]; $labelled++
  } elseif ($line -match 'Tracing Screenshot "(ScreenShot\d+)"' -and $pending) {
    $byFile[$Matches[1]] = $pending; $pending = $null
  }
}
$i = 0
foreach ($f in $shots) {
  $name = $byFile[$f.BaseName]
  if (-not $name) { $name = "unlabelled_" + $f.BaseName }
  Move-Item $f.FullName "$out\$name.png" -Force; $i++
}
"moved $i screenshots ($labelled labelled shots, $($byFile.Count) matched) to $out"
# packaged builds log no 'Tracing Screenshot' lines: align the files on the shot labels by time instead
if (Get-ChildItem $out -Filter "unlabelled_*.png") { & python "$PSScriptRoot\label_shots.py" $out }
"Accessed None: " + (Select-String -Path "$out\server.log" -Pattern 'Accessed None').Count
