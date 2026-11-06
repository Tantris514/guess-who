# Rendered QA of the pickups (s38_pickups.py -GWPickupShots): a windowed host walks to each pickup / interactable and
# takes "Shot showui" screenshots (balls on the felt, sword on the armour, sword in hand, safe closed / open, alarm box
# before / after, post-it, swap ghost, slash). Run it under LOCK GAMETEST (the caller writes the lock lines); never
# while the user plays. Shots: GuessWho\Saved\Screenshots\ (copied to Tools\gameplay\shots\pickups).
param([int]$Seconds = 75)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$log = "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\logs\pickup_shots.log"
$shots = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\Saved\Screenshots"
$out = "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\shots\pickups"
New-Item -ItemType Directory -Force $out | Out-Null
Remove-Item $log -ErrorAction SilentlyContinue
$t0 = Get-Date
$sargs = @("`"$uproject`"", "/Game/GW/Maps/L_Manor?listen?Name=Hote", '-game', '-windowed', '-ResX=1280', '-ResY=720', '-ForceRes',
           '-WinX=0', '-WinY=0', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-log', "-abslog=`"$log`"",
           '-GWDev', '-GWName=Hote', '-GWPickupTest', '-GWPickupShots', '-port=7792')
$s = Start-Process -FilePath $editor -ArgumentList $sargs -PassThru
"host pid $($s.Id)"
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ((Test-Path $log) -and (Select-String -Path $log -Pattern "GW: pickup test driver started" -Quiet)) { break }
  if ($s.HasExited) { "host exited early"; break }
}
"driver started after $([int]((Get-Date) - $t0).TotalSeconds)s"
Start-Sleep -Seconds $Seconds
if (-not $s.HasExited) { Stop-Process -Id $s.Id -Force }
Get-ChildItem $shots -Recurse -Filter *.png | Where-Object { $_.LastWriteTime -gt $t0 } | Sort-Object LastWriteTime |
  ForEach-Object -Begin { $i = 0 } -Process { $i++; Copy-Item $_.FullName (Join-Path $out ("shot_{0:D2}.png" -f $i)) -Force; "shot_{0:D2} <- $($_.Name)" -f $i }
"== AccessedNone=$((Select-String $log -Pattern 'Accessed None').Count) ScriptErrors=$((Select-String $log -Pattern 'LogScript: Error|Blueprint Runtime Error').Count) ScriptWarnings=$((Select-String $log -Pattern 'LogScript: Warning').Count)"
