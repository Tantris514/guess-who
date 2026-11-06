# Runs a plan of Tools\qa\py_harness.py in an editor -game on L_Manor, under LOCK GAMETEST. Usage: py_harness.ps1 -Plan zomb [-Render] [-Seconds 200]
param([string]$Plan, [switch]$Render, [int]$Seconds = 240, [string]$Extra = "", [int]$ResX = 1600, [int]$ResY = 900, [string]$Map = "/Game/GW/Maps/L_Manor?listen?port=7786?Name=Hote")
$root = "J:\Projets\Unreal_Projects\Guess Who"
$locks = "$root\Tools\agent_logs\locks.md"
$got = $false
$t0 = Get-Date
while (-not $got) {
  if (((Get-Date) - $t0).TotalMinutes -gt 30) { "gave up waiting"; exit 2 }
  python -I -X utf8 "$root\Tools\qa\locks_open.py" --quiet
  if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 10; continue }
  Add-Content $locks "LOCK GAMETEST items $(Get-Date -Format HH:mm) (py_harness $Plan, 5 min max)" -Encoding utf8
  Start-Sleep -Seconds 3
  $others = python -I -X utf8 "$root\Tools\qa\locks_open.py" | Where-Object { $_ -match '^LOCK ' -and $_ -notmatch '^LOCK GAMETEST items ' }
  if ($others) { Add-Content $locks "UNLOCK GAMETEST items $(Get-Date -Format HH:mm) (withdrawn)" -Encoding utf8; Start-Sleep -Seconds 20; continue }
  $got = $true
}
$log = "$root\Tools\qa\voice\pyh_$Plan`_$(Get-Date -Format yyyyMMdd_HHmmss).log"
$a = @("`"$root\GuessWho\GuessWho.uproject`"", $Map, '-game', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-port=7786',
       '-GWDev', '-GWName=Hote', "-GWHarness=$Plan", "-ExecCmds=`"py $root\Tools\qa\py_harness.py`"", '-log', "-abslog=`"$log`"")
if ($Extra) { $a += $Extra }
if ($Render) { $a += @('-windowed', "-ResX=$ResX", "-ResY=$ResY", '-ForceRes') } else { $a += '-nullrhi' }
$p = Start-Process -FilePath "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList $a -PassThru -WindowStyle Hidden
if (-not $p.WaitForExit($Seconds * 1000)) { "time limit reached"; Stop-Process -Id $p.Id -Force }
Add-Content $locks "UNLOCK GAMETEST items $(Get-Date -Format HH:mm)" -Encoding utf8
"log $log"
Select-String -Path $log -Pattern 'GWH:' | ForEach-Object { $_.Line -replace '^.*GWH: ', '' }
"Accessed None: $((Select-String -Path $log -Pattern 'Accessed None').Count)  script errors: $((Select-String -Path $log -Pattern 'LogScript: Error|Blueprint Runtime Error').Count)  script warnings: $((Select-String -Path $log -Pattern 'LogScript: Warning').Count)  LogBlueprint errors: $((Select-String -Path $log -Pattern 'LogBlueprint: Error').Count)"
