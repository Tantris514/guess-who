# Headless test of the mezzanine machine gun and the first-person view (no GPU, works while the user plays).
# -GWTurretTest runs BP_GW_PlayerController.TurretTestTick (s35_turret.py): test round as a guest, ammo, go to the gun,
# E (mount), aim at an NPC placed in the hall, a 2 s burst, E (dismount); then as a detective: mount, a 4.5 s trigger
# (the burst must stop at 3 s and start the 25 s recharge), a refused second burst, dismount; aim-down-sights rotation
# (GWAim 1 / 0); third person and back. -GWViewLog prints the view driver's state every second.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File Tools\gameplay\turret_test.ps1 [-Seconds 75] [-Log <path>]
param([int]$Seconds = 110, [string]$Log = 'J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\logs\turret_test.log')
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$exe = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$proj = "$root\GuessWho\GuessWho.uproject"
New-Item -ItemType Directory -Force (Split-Path $Log) | Out-Null
if (Test-Path $Log) { Remove-Item $Log -Force }
$argList = @("`"$proj`"", '/Game/GW/Maps/L_Manor?listen?Name=Hote', '-game', '-nullrhi', '-nosound', '-unattended', '-nosplash',
    '-NoLiveCoding', '-GWDev', '-GWTurretTest', '-GWViewLog', '-GWName=Hote', '-log', "-abslog=`"$Log`"")
$p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -WindowStyle Hidden
if (-not $p.WaitForExit($Seconds * 1000)) { Stop-Process -Id $p.Id -Force }
Start-Sleep -Seconds 2
$text = Get-Content $Log -Raw -ErrorAction SilentlyContinue
$n = { param($pat) ([regex]::Matches($text, $pat)).Count }
"AccessedNone: " + (& $n 'Accessed None')
"BP errors: " + (& $n 'LogScript: Error|Blueprint Runtime Error')
"Script warnings: " + (& $n 'LogScript: Warning')
"spawned: " + (& $n 'GW: turret spawned') + "  mounted: " + (& $n 'GW: turret mounted by') + "  dismounted: " + (& $n 'GW: turret dismounted')
"NPC kills (guest): " + (& $n 'GW: turret kill NPC') + "  detective hits: " + (& $n 'GW: turret \(detective\) hit') + "  panic: " + (& $n 'GW: turret burst panics')
"burst over: " + (& $n 'GW: turret burst over') + "  refused cooldown: " + (& $n 'GW: turret refused \(detective cooldown') + "  empty: " + (& $n 'GW: turret empty')
"view lines: " + (& $n 'GW view:')
Select-String -Path $Log -Pattern 'GW turrettest|GW: turret|GW view: (new|server|aiming|first)|Accessed None|LogScript: (Error|Warning)|Blueprint Runtime Error' |
    ForEach-Object { $_.Line -replace '^\[[^\]]*\]\[[^\]]*\]', '' } | Select-Object -First 140
