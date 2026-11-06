# Headless test of the events round (s40_events2.py EvTestTick, -GWEvTest): kamikaze followed by the camera, E on guests, dance,
# bandits leaving, breakers, fire, zombies. Port 7788. GAMETEST lock rules as in voice_test.ps1.
# Usage: powershell -File Tools\qa\ev_test.ps1 [-Tag x] [-NPCs 30]
param([string]$Tag = "", [int]$NPCs = 0, [switch]$Render)
$root = "J:\Projets\Unreal_Projects\Guess Who"
$locks = "$root\Tools\agent_logs\locks.md"
$got = $false
$t0 = Get-Date
while (-not $got) {
  if (((Get-Date) - $t0).TotalMinutes -gt 40) { "gave up waiting"; exit 2 }
  python -I -X utf8 "$root\Tools\qa\locks_open.py" --quiet
  if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 10; continue }
  Add-Content $locks "LOCK GAMETEST events $(Get-Date -Format HH:mm) (ev_test, 5 min max)" -Encoding utf8
  Start-Sleep -Seconds 3
  $others = python -I -X utf8 "$root\Tools\qa\locks_open.py" | Where-Object { $_ -match '^LOCK ' -and $_ -notmatch '^LOCK GAMETEST events ' }
  if ($others) { Add-Content $locks "UNLOCK GAMETEST events $(Get-Date -Format HH:mm) (withdrawn)" -Encoding utf8; Start-Sleep -Seconds 20; continue }
  $got = $true
}
$log = "$root\Tools\qa\voice\ev_$Tag$(Get-Date -Format yyyyMMdd_HHmmss).log"
$map = "/Game/GW/Maps/L_Manor?listen?port=7788?Name=Hote"; if ($NPCs -gt 0) { $map += "?NPCs=$NPCs" }
$a = @("`"$root\GuessWho\GuessWho.uproject`"", $map, '-game', '-nullrhi', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-port=7788',
       '-GWDev', '-GWName=Hote', '-GWEvTest', '-log', "-abslog=`"$log`"")
if ($Render) { $a = ($a | Where-Object { $_ -ne '-nullrhi' }) + @('-windowed', '-ResX=1600', '-ResY=900', '-ForceRes', '-GWDevShot') }
$p = Start-Process -FilePath "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList $a -PassThru -WindowStyle Hidden
if (-not $p.WaitForExit(290 * 1000)) { "5 min reached"; Stop-Process -Id $p.Id -Force }
Add-Content $locks "UNLOCK GAMETEST events $(Get-Date -Format HH:mm)" -Encoding utf8
"log $log"
"Accessed None: $((Select-String -Path $log -Pattern 'Accessed None').Count)  script errors: $((Select-String -Path $log -Pattern 'LogScript: Error|Blueprint Runtime Error').Count)  script warnings: $((Select-String -Path $log -Pattern 'LogScript: Warning').Count)"
