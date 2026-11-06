# Rendered costume review: listen server on L_Manor with -GWLineup (BP_GW_Showcase), no client. Copies the "Shot" images.
param([string]$Tag = "costume", [int]$ResX = 1600, [int]$ResY = 900, [int]$Seconds = 110)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$proj = "J:\Projets\Unreal_Projects\Guess Who\GuessWho"
$out = "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\shots\$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
$start = Get-Date
$sargs = @("`"$uproject`"", "/Game/GW/Maps/L_Manor?listen?NPCs=24?Name=Hote", '-game', '-windowed', "-ResX=$ResX", "-ResY=$ResY", '-nosplash',
           '-unattended', '-NoLiveCoding', '-nosound', '-GWLineup', '-GWName=Hote', '-log', "-abslog=`"$out\server.log`"")
$s = Start-Process -FilePath $editor -ArgumentList $sargs -PassThru
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ((Test-Path "$out\server.log") -and (Select-String -Path "$out\server.log" -Pattern "GW: showcase running" -Quiet)) { break }
  if ($s.HasExited) { "server exited early"; break }
}
$null = $s.WaitForExit($Seconds * 1000)
if (-not $s.HasExited) { Stop-Process -Id $s.Id -Force }
Start-Sleep -Seconds 1
$shots = Get-ChildItem "$proj\Saved\Screenshots" -Recurse -Filter *.png | Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime
$i = 0
foreach ($f in $shots) { Copy-Item $f.FullName "$out\shot_$i.png"; $i++ }
"copied $i screenshots to $out"
"Accessed None: " + (Select-String -Path "$out\server.log" -Pattern 'Accessed None').Count
