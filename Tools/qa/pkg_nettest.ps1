# Network test on the PACKAGED game: listen server + 1 client of Build\Windows\GuessWho.exe, headless, with the
# gameplay autotest bots. Logs go to Tools\qa\pkg_logs. Usage: powershell -File pkg_nettest.ps1 [-Seconds 150]
param(
  [int]$Seconds = 150,
  [string]$Opts = "?HideTime=6?HuntTime=50?EndTime=4?LobbyTime=3",
  [string]$Render = "",   # "-Render" keeps rendering on (windowed) instead of -nullrhi
  [string]$BuildDir = "J:\Projets\Unreal_Projects\Guess Who\Build\Windows"   # any packaged build folder (e.g. Build_next\Windows)
)
$exe = "$BuildDir\GuessWho.exe"
$dir = "J:\Projets\Unreal_Projects\Guess Who\Tools\qa\pkg_logs"
if (-not (Test-Path $exe)) { "packaged exe not found: $exe"; exit 2 }
# another listen server on 7777 (an editor -game test) would take our client: 2026-11-03 07:11 smoke test
$busy = Get-NetUDPEndpoint -LocalPort 7777 -ErrorAction SilentlyContinue
if ($busy) { "port 7777 busy (pid $(($busy | Select-Object -First 1).OwningProcess)): another game server is running"; exit 3 }
New-Item -ItemType Directory -Force $dir | Out-Null
Remove-Item "$dir\server.log","$dir\client.log" -ErrorAction SilentlyContinue
$common = @('-nosound', '-unattended', '-nosplash', '-log')
if ($Render -eq "-Render") { $common += @('-windowed', '-ResX=960', '-ResY=540') } else { $common += '-nullrhi' }
$sargs = @("/Game/GW/Maps/L_Manor?listen$Opts?Name=Hote") + $common + @("-abslog=`"$dir\server.log`"", "-GWAutoTest", "-GWName=Hote")
$s = Start-Process -FilePath $exe -ArgumentList $sargs -PassThru -WindowStyle Minimized
"server pid $($s.Id)"
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ((Test-Path "$dir\server.log") -and (Select-String -Path "$dir\server.log" -Pattern "GW: game mode ready" -Quiet)) { break }
  if ($s.HasExited) { "server exited early (code $($s.ExitCode))"; break }
}
"server ready after $([int]((Get-Date) - $s.StartTime).TotalSeconds)s"
$cargs = @("127.0.0.1?Name=Invite2") + $common + @("-abslog=`"$dir\client.log`"", "-GWAutoTest", "-GWName=Invite2")
$c = Start-Process -FilePath $exe -ArgumentList $cargs -PassThru -WindowStyle Minimized
"client pid $($c.Id)"
Start-Sleep -Seconds $Seconds
foreach ($p in @($c, $s)) { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
# GuessWho.exe is a small launcher; the real process is GuessWho-Win64-*.exe / UnrealGame. Kill leftovers we started.
Get-Process | Where-Object { $_.Path -like "$BuildDir\*" } | Stop-Process -Force -ErrorAction SilentlyContinue
"killed"
foreach ($f in "server.log", "client.log") {
  $p = "$dir\$f"
  if (-not (Test-Path $p)) { "$f missing"; continue }
  "== $f : Accessed None=$((Select-String $p -Pattern 'Accessed None').Count) BP runtime errors=$((Select-String $p -Pattern 'Blueprint Runtime Error').Count) Fatal=$((Select-String $p -Pattern 'Fatal error|Assertion failed').Count)"
  Select-String $p -Pattern "GW: round|GW: .*abattu|GW: round over|LoadMap:|Welcomed by server|Join succeeded|NetworkFailure|TravelFailure" | Select-Object -First 14 | ForEach-Object { $l = $_.Line; $i = $l.IndexOf("]Log"); if ($i -ge 0) { $l.Substring($i + 1) } else { $l } }
}
