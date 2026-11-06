# Rendered camera screenshots: listen server rendered (windowed, -GWCamTest hook in BP_GW_Character), one headless client.
param([string]$Tag = "cam", [int]$ResX = 1280, [int]$ResY = 720, [int]$Seconds = 120,
      [string]$Opts = "?HideTime=8?HuntTime=25?EndTime=4?LobbyTime=4")
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$proj = "J:\Projets\Unreal_Projects\Guess Who\GuessWho"
$out = "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\shots\$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
$start = Get-Date
$sargs = @("`"$uproject`"", "/Game/GW/Maps/L_Manor?listen${Opts}?Name=Hote", '-game', '-windowed', "-ResX=$ResX", "-ResY=$ResY", '-nosplash',
           '-unattended', '-NoLiveCoding', '-nosound', '-GWName=Hote', '-GWCamTest', '-log', "-abslog=`"$out\server.log`"")
$s = Start-Process -FilePath $editor -ArgumentList $sargs -PassThru
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ((Test-Path "$out\server.log") -and (Select-String -Path "$out\server.log" -Pattern "GW: game mode ready" -Quiet)) { break }
  if ($s.HasExited) { "server exited early"; break }
}
$cargs = @("`"$uproject`"", "127.0.0.1?Name=Invite2", '-game', '-nullrhi', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-log',
           "-abslog=`"$out\client.log`"", '-GWName=Invite2')
$c = Start-Process -FilePath $editor -ArgumentList $cargs -PassThru
$done = $s.WaitForExit($Seconds * 1000)
foreach ($p in @($c, $s)) { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
Start-Sleep -Seconds 1
$shots = Get-ChildItem "$proj\Saved\Screenshots" -Recurse -Filter *.png | Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime
$i = 0
foreach ($f in $shots) { Copy-Item $f.FullName "$out\shot_$i.png"; $i++ }
"copied $i screenshots to $out (server exited by itself: $done)"
foreach ($f in 'server.log', 'client.log') { "$f Accessed None: " + (Select-String -Path "$out\$f" -Pattern 'Accessed None').Count }
