# Short rendered -game run that takes HighResShot screenshots through the -GWShot dev hook, then copies them to Tools/ui/shots/<Tag>.
# Usage: powershell -File shot.ps1 -Tag menu_169 [-Map /Game/GW/Maps/L_MainMenu] [-ResX 1280] [-ResY 720] [-Seconds 60] [-Extra "-GWAutoTest"]
param(
  [string]$Tag = "menu",
  [string]$Map = "/Game/GW/Maps/L_MainMenu",
  [int]$ResX = 1280,
  [int]$ResY = 720,
  [int]$Seconds = 60,
  [string]$Extra = "-ForceRes -WinX=0 -WinY=0"
)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$proj = "J:\Projets\Unreal_Projects\Guess Who\GuessWho"
$out = "J:\Projets\Unreal_Projects\Guess Who\Tools\ui\shots\$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
$log = "$out\run.log"
$start = Get-Date
$args = @("`"$uproject`"", $Map, '-game', '-windowed', "-ResX=$ResX", "-ResY=$ResY", '-nosplash', '-unattended', '-NoLiveCoding',
          '-nosound', '-GWShot', '-log', "-abslog=`"$log`"") + ($Extra.Split(" ") | Where-Object { $_ })
$p = Start-Process -FilePath $editor -ArgumentList $args -PassThru
$done = $p.WaitForExit($Seconds * 1000)
if (-not $done) { Stop-Process -Id $p.Id -Force; "timeout: killed" }
Start-Sleep -Seconds 1
$shots = Get-ChildItem "$proj\Saved\Screenshots" -Recurse -Filter *.png | Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime
$i = 0
foreach ($s in $shots) { Copy-Item $s.FullName "$out\shot_$i.png"; $i++ }
"copied $i screenshots to $out"
Select-String -Path $log -Pattern "Error|Accessed None|Script Msg" | Select-Object -First 15 | ForEach-Object { $_.Line.Substring(0, [Math]::Min(220, $_.Line.Length)) }
