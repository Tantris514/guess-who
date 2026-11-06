# Pickups & interactables test (s38_pickups.py), headless (-nullrhi), uncooked project, run it under LOCK GAMETEST (<= 5 min; the caller writes the lock lines).
#  -Solo : one listen-server host with -GWPickupTest -GWPickupSolo (guest vs NPCs: balls, sword, 2 swaps, post-it, safe,
#          fire alarm twice, toilet, fart).
#  else  : host + client, both -GWPickupTest: host = detective, client = guest (throw / slash an NPC and the host, swap
#          with the client camera following, post-it, safe, toilet).
# Usage: powershell -File s38_nettest.ps1 [-Solo] [-Seconds 150]
param(
  [int]$Seconds = 150,
  [switch]$Solo
)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$dir = "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\logs"
$locks = "J:\Projets\Unreal_Projects\Guess Who\Tools\agent_logs\locks.md"
New-Item -ItemType Directory -Force $dir | Out-Null
$tag = if ($Solo) { "solo" } else { "net" }
$slog = "$dir\pickup_${tag}_server.log"; $clog = "$dir\pickup_${tag}_client.log"
Remove-Item $slog, $clog -ErrorAction SilentlyContinue
$common = @('-game', '-nullrhi', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-log', '-NoVerifyGC', '-GWPickupTest')
$sargs = @("`"$uproject`"", "/Game/GW/Maps/L_Manor?listen?Name=Hote") + $common + @("-abslog=`"$slog`"", '-GWDev', '-GWName=Hote', '-port=7792')
if ($Solo) { $sargs += '-GWPickupSolo' }
$s = Start-Process -FilePath $editor -ArgumentList $sargs -PassThru -WindowStyle Minimized
"server pid $($s.Id)"
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ((Test-Path $slog) -and (Select-String -Path $slog -Pattern "GW: game mode ready" -Quiet)) { break }
  if ($s.HasExited) { "server exited early"; break }
}
"server ready after $([int]((Get-Date) - $s.StartTime).TotalSeconds)s"
$c = $null
if (-not $Solo) {
  $cargs = @("`"$uproject`"", "127.0.0.1:7792?Name=Invite2") + $common + @("-abslog=`"$clog`"", '-GWName=Invite2')
  $c = Start-Process -FilePath $editor -ArgumentList $cargs -PassThru -WindowStyle Minimized
  "client pid $($c.Id)"
}
Start-Sleep -Seconds $Seconds
foreach ($p in @($c, $s)) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
"killed"
foreach ($f in @($slog, $clog)) {
  if (-not (Test-Path $f)) { continue }
  "== $(Split-Path $f -Leaf): AccessedNone=$((Select-String $f -Pattern 'Accessed None').Count) ScriptErrors=$((Select-String $f -Pattern 'LogScript: Error|Blueprint Runtime Error').Count) ScriptWarnings=$((Select-String $f -Pattern 'LogScript: Warning').Count) Fatal=$((Select-String $f -Pattern 'Fatal error|Assertion failed').Count)"
}
