# Headless check of the robot (s32, BP_GW_RobotController): runs the automated dev-menu sequence (-GWDevTest), whose
# step 91 spawns the robot 8 m in front of the (respawned) host; the robot must spot him and fire its laser.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File Tools\gameplay\robot_test.ps1 [-Seconds 260]
param([int]$Seconds = 260, [string]$Log = 'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\logs\robot_test.log')
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$exe = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$proj = "$root\GuessWho\GuessWho.uproject"
New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
if (Test-Path $Log) { Remove-Item $Log -Force }
$argList = @("`"$proj`"", '/Game/GW/Maps/L_Manor?listen?Name=Hote', '-game', '-nullrhi', '-nosound', '-unattended', '-nosplash',
    '-NoLiveCoding', '-GWDev', '-GWDevTest', '-GWName=Hote', '-log', "-abslog=`"$Log`"")
$p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -WindowStyle Hidden
$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline -and -not $p.HasExited) {
    Start-Sleep -Seconds 5
    if ((Test-Path $Log) -and (Select-String -Path $Log -Pattern 'GW devtest step 100 ' -Quiet)) { Start-Sleep -Seconds 3; break }
}
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
Start-Sleep -Seconds 2
$text = Get-Content $Log -Raw -ErrorAction SilentlyContinue
$n = { param($pat) ([regex]::Matches($text, $pat)).Count }
"AccessedNone: " + (& $n 'Accessed None')
"BP errors: " + (& $n 'LogScript: Error|Blueprint Runtime Error')
"Script warnings: " + (& $n 'LogScript: Warning')
"robot test spawned: " + (& $n 'robot test: spawned') + "  spotted: " + (& $n 'GW: robot spotted') + "  fires: " + (& $n 'GW: robot fires at') + "  laser sound (world sound cat=26): " + (& $n 'world sound cat=26')
Select-String -Path $Log -Pattern 'devtest step (8[89]|9[0-9]|100) |robot|respawn|cat=26|Accessed None|LogScript: (Error|Warning)' |
    ForEach-Object { $_.Line -replace '^\[[^\]]*\]\[[^\]]*\]', '' } | Select-Object -First 50
