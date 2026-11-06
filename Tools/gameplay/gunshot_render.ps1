# Rendered look at the first-person view, the guns and the machine gun (editor -game with a GPU; NOT while the user
# plays). -GWGunShot runs BP_GW_PlayerController.ViewTestTick (s37_view.py): test round as a detective in the ballroom,
# first-person hip shot, aim-down-sights shot, NPCs in the detective look filmed at the right hand (side, front, close),
# third-person option, then the gallery machine gun: a burst through the sight (HUD on) and seen from the hall floor.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File Tools\gameplay\gunshot_render.ps1 [-Tag gun1] [-Seconds 75]
param([string]$Tag = 'gun1', [int]$Seconds = 90)   # listen port 7791: never the game's 7777
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$exe = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$proj = "$root\GuessWho\GuessWho.uproject"
$out = "$root\Tools\gameplay\shots\$Tag"
New-Item -ItemType Directory -Force $out | Out-Null
$shots = "$root\GuessWho\Saved\Screenshots"
$start = Get-Date
$log = Join-Path $out 'game.log'
$argList = @("`"$proj`"", '/Game/GW/Maps/L_Manor?listen?Name=Hote', '-game', '-windowed', '-ResX=1600', '-ResY=900', '-ForceRes',
    '-nosplash', '-unattended', '-NoLiveCoding', '-nosound', '-GWDev', '-GWGunShot', '-GWViewLog', '-GWName=Hote', '-port=7791', '-log', "-abslog=`"$log`"")
$p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru
if (-not $p.WaitForExit($Seconds * 1000)) { Stop-Process -Id $p.Id -Force }
Start-Sleep -Seconds 2
$i = 0
if (Test-Path $shots) {
    Get-ChildItem $shots -Recurse -Filter *.png | Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $out ("shot_{0}.png" -f $i)); $i++
    }
}
$text = Get-Content $log -Raw -ErrorAction SilentlyContinue
$n = { param($pat) ([regex]::Matches($text, $pat)).Count }
"shots: $i -> $out"
"AccessedNone: " + (& $n 'Accessed None')
"BP errors: " + (& $n 'LogScript: Error|Blueprint Runtime Error')
"Script warnings: " + (& $n 'LogScript: Warning')
Select-String -Path $log -Pattern 'GW viewshot|GW: turret' | ForEach-Object { $_.Line -replace '^\[[^\]]*\]\[[^\]]*\]', '' } | Select-Object -First 60
