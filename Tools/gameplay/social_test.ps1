# Headless social-life test (s36_social.py): listen server on L_Manor running the -GWSocialTest script (dances,
# moving stops it, NPC dance and bar groups, a kill, a blackout panic, groups forming and dispersing) and a client
# (-GWSocialWatch) that dances through ServerExec and logs what it sees. Own port 17777: never joins a real game.
# -Shots: a RENDERED host instead (-GWDanceShots: ghost camera over the dance floor and the bar, HighResShot x9 to
#   GuessWho\Saved\Screenshots); refused while the packaged game (UnrealGame) runs.
# One game test at a time machine-wide: takes LOCK GAMETEST in locks.md (refuses if someone holds it), <= 5 min total.
# Usage: powershell -File social_test.ps1 [-Seconds 205] [-NoClient] [-Shots]
param([int]$Seconds = 205, [switch]$NoClient, [switch]$Shots)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$dir = "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\logs"
$locks = "J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\locks.md"
New-Item -ItemType Directory -Force $dir | Out-Null
$last = Select-String -Path $locks -Pattern '^(UN)?LOCK GAMETEST' | Select-Object -Last 1
if ($last -and $last.Line -like 'LOCK GAMETEST*') { "GAMETEST held: $($last.Line)"; exit 3 }
if ($Shots -and (Get-Process UnrealGame -ErrorAction SilentlyContinue)) { "the user is playing (UnrealGame): no rendered test"; exit 2 }
[IO.File]::AppendAllText($locks, "LOCK GAMETEST social $(Get-Date -Format HH:mm)`n")
Start-Sleep -Seconds 2
# race rule: if someone else's LOCK GAMETEST is open before mine, step back and let them run
$open = @()
foreach ($l in (Select-String -Path $locks -Pattern '^(UN)?LOCK GAMETEST (\S+)')) {
  $who = $l.Matches[0].Groups[2].Value
  if ($l.Line -like 'LOCK*') { $open += $who } else { $open = @($open | Where-Object { $_ -ne $who }) }
}
if ($open.Count -gt 0 -and $open[0] -ne 'social') {
  [IO.File]::AppendAllText($locks, "UNLOCK GAMETEST social $(Get-Date -Format HH:mm) (race: $($open[0]) first)`n")
  "GAMETEST race lost to $($open[0])"; exit 3
}
$t0 = Get-Date
if ($Shots) {
  Remove-Item "$dir\social_shots.log" -ErrorAction SilentlyContinue
  $a = @("`"$uproject`"", "/Game/GW/Maps/L_Manor?listen?Name=Hote", '-port=17778', '-GWDev', '-GWName=Hote', '-GWDanceShots',
         '-game', '-windowed', '-ResX=1600', '-ResY=900', '-ForceRes', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding',
         '-log', "-abslog=`"$dir\social_shots.log`"")
  $s = Start-Process -FilePath $editor -ArgumentList $a -PassThru
  "rendered host pid $($s.Id)"
  Start-Sleep -Seconds ([Math]::Min([Math]::Max($Seconds, 200), 280))
  if (-not $s.HasExited) { Stop-Process -Id $s.Id -Force }
  [IO.File]::AppendAllText($locks, "UNLOCK GAMETEST social $(Get-Date -Format HH:mm)`n")
  Select-String -Path "$dir\social_shots.log" -Pattern "Tracing Screenshot|HighResShot|screenshot" | Select-Object -Last 12
  exit 0
}
Remove-Item "$dir\social_host.log","$dir\social_client.log" -ErrorAction SilentlyContinue
$common = @('-game', '-nullrhi', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-log', '-NoVerifyGC')
$sargs = @("`"$uproject`"", "/Game/GW/Maps/L_Manor?listen?Name=Hote", '-port=17777', '-GWDev', '-GWName=Hote', '-GWSocialTest') + $common + @("-abslog=`"$dir\social_host.log`"")
$s = Start-Process -FilePath $editor -ArgumentList $sargs -PassThru -WindowStyle Minimized
"host pid $($s.Id)"
$c = $null
if (-not $NoClient) {
  $deadline = (Get-Date).AddSeconds(150)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    if ((Test-Path "$dir\social_host.log") -and (Select-String -Path "$dir\social_host.log" -Pattern "GW: game mode ready" -Quiet)) { break }
    if ($s.HasExited) { "host exited early"; break }
  }
  "host ready after $([int]((Get-Date) - $s.StartTime).TotalSeconds)s"
  $cargs = @("`"$uproject`"", "127.0.0.1:17777?Name=Danseur", '-GWName=Danseur', '-GWSocialWatch') + $common + @("-abslog=`"$dir\social_client.log`"")
  $c = Start-Process -FilePath $editor -ArgumentList $cargs -PassThru -WindowStyle Minimized
  "client pid $($c.Id)"
}
$left = 295 - [int]((Get-Date) - $t0).TotalSeconds
Start-Sleep -Seconds ([Math]::Max(10, [Math]::Min($Seconds, $left)))
foreach ($p in @($c, $s)) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
"killed after $([int]((Get-Date) - $t0).TotalSeconds) s"
[IO.File]::AppendAllText($locks, "UNLOCK GAMETEST social $(Get-Date -Format HH:mm)`n")
foreach ($f in @("$dir\social_host.log", "$dir\social_client.log")) {
  if (Test-Path $f) {
    $n = @{}
    foreach ($pat in @('Accessed None', 'LogScript: Error', 'Blueprint Runtime Error', 'LogScript: Warning')) {
      $n[$pat] = @(Select-String -Path $f -Pattern $pat -SimpleMatch).Count
    }
    "$f : " + (($n.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ', ')
  }
}
