# Host + client, headless: NPC pops, relevancy and movement on the client's side (Tools\qa\npc_watch.py, plans npchost100 / npcclient). Under LOCK GAMETEST.
param([int]$Seconds = 300)
$root = "J:\Projets\Unreal_Projects\Guess Who"
$locks = "$root\Tools\agent_logs\locks.md"
$got = $false
$t0 = Get-Date
while (-not $got) {
  if (((Get-Date) - $t0).TotalMinutes -gt 30) { "gave up waiting"; exit 2 }
  python -I -X utf8 "$root\Tools\qa\locks_open.py" --quiet
  if ($LASTEXITCODE -ne 0) { Start-Sleep -Seconds 10; continue }
  Add-Content $locks "LOCK GAMETEST feedback6_npc $(Get-Date -Format HH:mm) (npc_net, 6 min max)" -Encoding utf8
  Start-Sleep -Seconds 3
  $others = python -I -X utf8 "$root\Tools\qa\locks_open.py" | Where-Object { $_ -match '^LOCK ' -and $_ -notmatch '^LOCK GAMETEST feedback6_npc ' }
  if ($others) { Add-Content $locks "UNLOCK GAMETEST feedback6_npc $(Get-Date -Format HH:mm) (withdrawn)" -Encoding utf8; Start-Sleep -Seconds 20; continue }
  $got = $true
}
$stamp = Get-Date -Format yyyyMMdd_HHmmss
$slog = "$root\Tools\qa\voice\npcnet_host_$stamp.log"; $clog = "$root\Tools\qa\voice\npcnet_client_$stamp.log"
$editor = "$root\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$up = "`"$root\GuessWho\GuessWho.uproject`""
$py = "-ExecCmds=`"py $root\Tools\qa\py_harness.py`""
$common = @('-game', '-nullrhi', '-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-log')
$s = Start-Process -FilePath $editor -ArgumentList (@($up, "/Game/GW/Maps/L_Manor?listen?port=7788?Name=Hote", '-port=7788', '-GWDev', '-GWName=Hote', '-GWHarness=npchost100', $py, "-abslog=`"$slog`"") + $common) -PassThru -WindowStyle Hidden
$deadline = (Get-Date).AddSeconds(150)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Seconds 3
  if ((Test-Path $slog) -and (Select-String -Path $slog -Pattern "GW: game mode ready|GWH: plan" -Quiet)) { break }
}
$c = Start-Process -FilePath $editor -ArgumentList (@($up, "127.0.0.1:7788?Name=Invite2", '-GWName=Invite2', '-GWHarness=npcclient', $py, "-abslog=`"$clog`"") + $common) -PassThru -WindowStyle Hidden
[void]$c.WaitForExit($Seconds * 1000)
foreach ($p in @($c, $s)) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force } }
Add-Content $locks "UNLOCK GAMETEST feedback6_npc $(Get-Date -Format HH:mm)" -Encoding utf8
"host $slog"; "client $clog"
foreach ($f in @($clog, $slog)) {
  "== $(Split-Path $f -Leaf)"
  Select-String -Path $f -Pattern 'GWH: NW (REPORT|events|still|same|moving|state|room|longest|census)' | ForEach-Object { $_.Line -replace '^.*?GWH: ', '' } | Select-Object -Last 11
  "Accessed None: $((Select-String -Path $f -Pattern 'Accessed None').Count)  script errors: $((Select-String -Path $f -Pattern 'LogScript: Error|Blueprint Runtime Error').Count)  script warnings: $((Select-String -Path $f -Pattern 'LogScript: Warning').Count)  LogBlueprint errors: $((Select-String -Path $f -Pattern 'LogBlueprint: Error').Count)"
}
