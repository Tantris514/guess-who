# Rendered run of the automated dev-menu test (DevTestTick, steps 3-102: menu, round, test round, piano, events) in
# the editor's -game mode, with screenshots: the Partie page, the ghost, and every event 2.5 s in after the camera
# was taken to it (GWDevEventGo). Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File Tools\qa\devmenu_render.ps1 -Out Tools\qa\devmenu\events_render2 [-Seconds 280]
param([Parameter(Mandatory = $true)][string]$Out, [int]$Seconds = 280)
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$exe = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$proj = "$root\GuessWho\GuessWho.uproject"
if (-not [System.IO.Path]::IsPathRooted($Out)) { $Out = Join-Path $root $Out }
New-Item -ItemType Directory -Force $Out | Out-Null
$shots = "$root\GuessWho\Saved\Screenshots"
$start = Get-Date
$log = Join-Path $Out 'game.log'
$argList = @("`"$proj`"", '/Game/GW/Maps/L_Manor?listen?Name=Hote', '-game', '-windowed', '-ResX=1600', '-ResY=900', '-ForceRes',
    '-nosplash', '-unattended', '-NoLiveCoding', '-nosound', '-GWDevTest', '-GWDevShot', '-GWName=Hote', '-log', "-abslog=`"$log`"")
$p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru
if (-not $p.WaitForExit($Seconds * 1000)) { Stop-Process -Id $p.Id -Force }
Start-Sleep -Seconds 2
$i = 0
if (Test-Path $shots) {
    Get-ChildItem $shots -Recurse -Filter *.png | Where-Object { $_.LastWriteTime -gt $start } | Sort-Object LastWriteTime | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $Out ("shot_{0}.png" -f $i)); $i++
    }
}
$text = Get-Content $log -Raw -ErrorAction SilentlyContinue
$n = { param($pat) ([regex]::Matches($text, $pat)).Count }
"shots: $i"
"AccessedNone: " + (& $n 'Accessed None')
"BP errors: " + (& $n 'LogScript: Error|Blueprint Runtime Error')
"Script warnings: " + (& $n 'LogScript: Warning')
"piano: " + (& $n 'GW: piano played by') + "  npc to piano: " + (& $n 'walks to the piano') + "  event go: " + (& $n 'went to the event')
"music: " + ((& $n 'GW music: state \d+ -> 1[1-5]'))
