# Two-process network test (listen server + 1 client) on the uncooked project, -nullrhi.
# Usage: powershell -File nettest.ps1 [-Map /Game/GW/Maps/Dev/L_GameplayTest] [-Seconds 120] [-Opts "?HideTime=5..."]
param(
  [string]$Map = "/Game/GW/Maps/Dev/L_GameplayTest",
  [int]$Seconds = 120,
  [string]$Opts = "?HideTime=5?HuntTime=45?EndTime=4?LobbyTime=3?NPCs=12",
  [string]$ServerExtra = "-GWAutoTest -GWName=Hote",
  [string]$ClientExtra = "-GWAutoTest -GWName=Invite2",
  [int]$ClientSeconds = 0
)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$dir = "J:\Projets\Unreal_Projects\Guess Who\Tools\ui\logs"
New-Item -ItemType Directory -Force $dir | Out-Null
Remove-Item "$dir\server.log","$dir\client.log" -ErrorAction SilentlyContinue
$common = @('-game', '-nullrhi', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-log', '-NoVerifyGC')
$sargs = @("`"$uproject`"", "$Map`?listen$Opts`?Name=Hote") + $common + @("-abslog=`"$dir\server.log`"") + $ServerExtra.Split(" ")
$s = Start-Process -FilePath $editor -ArgumentList $sargs -PassThru -WindowStyle Minimized
"server pid $($s.Id)"
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ((Test-Path "$dir\server.log") -and (Select-String -Path "$dir\server.log" -Pattern "GW: game mode ready" -Quiet)) { break }
  if ($s.HasExited) { "server exited early"; break }
}
"server ready after $([int]((Get-Date) - $s.StartTime).TotalSeconds)s"
$cargs = @("`"$uproject`"", "127.0.0.1?Name=Invite2") + $common + @("-abslog=`"$dir\client.log`"") + $ClientExtra.Split(" ")
$c = Start-Process -FilePath $editor -ArgumentList $cargs -PassThru -WindowStyle Minimized
"client pid $($c.Id)"
if ($ClientSeconds -gt 0 -and $ClientSeconds -lt $Seconds) {
  Start-Sleep -Seconds $ClientSeconds
  if (-not $c.HasExited) { Stop-Process -Id $c.Id -Force }
  "client killed at $ClientSeconds s"
  Start-Sleep -Seconds ($Seconds - $ClientSeconds)
} else { Start-Sleep -Seconds $Seconds }
foreach ($p in @($c, $s)) { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
"killed"
