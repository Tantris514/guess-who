# EOS code-game test on the PACKAGED game: one instance hosts (logs a code), a second one with its own device identity
# joins with that code. -NoRelay allows direct P2P; the default forces Epic's relays, the closest thing to two networks
# on one PC. Prints filtered logs only (no credentials reach the logs). Usage: powershell -File eos_test.ps1 [-Seconds 90]
param([int]$Seconds = 90, [switch]$NoRelay, [string]$BuildDir = "J:\Projets\Unreal_Projects\Guess Who\Build\Windows")
$exe = "$BuildDir\GuessWho.exe"
$dir = "J:\Projets\Unreal_Projects\Guess Who\Tools\qa\pkg_logs"
New-Item -ItemType Directory -Force $dir | Out-Null
Remove-Item "$dir\eos_host.log", "$dir\eos_join.log" -ErrorAction SilentlyContinue
$common = @('-nosound', '-unattended', '-nosplash', '-log', '-nullrhi', '-GWAutoTest')
if (-not $NoRelay) { $common += '-ini:Engine:[SocketSubsystemEOS]:RelayControl=ForceRelays' }
$h = Start-Process -FilePath $exe -ArgumentList ($common + @('-GWEOSHost', "-abslog=`"$dir\eos_host.log`"")) -PassThru -WindowStyle Minimized
$code = $null
$deadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $deadline -and -not $code) {
  Start-Sleep -Seconds 2
  if (Test-Path "$dir\eos_host.log") {
    $m = Select-String -Path "$dir\eos_host.log" -Pattern 'GWEOS: code=(\w+)' | Select-Object -First 1
    if ($m) { $code = $m.Matches[0].Groups[1].Value }
  }
  if ($h.HasExited) { break }
}
"code: $code"
if ($code) {
  # let the host finish loading the manor and start listening
  $deadline = (Get-Date).AddSeconds(90)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 2
    if (Select-String -Path "$dir\eos_host.log" -Pattern 'GW: game mode ready' -Quiet) { break }
  }
  $j = Start-Process -FilePath $exe -ArgumentList ($common + @("-GWEOSJoin=$code", '-GWEOSNewDevice', "-abslog=`"$dir\eos_join.log`"")) -PassThru -WindowStyle Minimized
  Start-Sleep -Seconds $Seconds
}
Get-Process | Where-Object { $_.Path -like "$BuildDir\*" } | Stop-Process -Force -ErrorAction SilentlyContinue
foreach ($f in 'eos_host.log', 'eos_join.log') {
  $p = "$dir\$f"
  if (-not (Test-Path $p)) { "$f missing"; continue }
  "== $f : Accessed None=$((Select-String $p -Pattern 'Accessed None').Count) BP errors=$((Select-String $p -Pattern 'Blueprint Runtime Error').Count) Fatal=$((Select-String $p -Pattern 'Fatal error|Assertion failed').Count)"
  Select-String $p -Pattern 'GWEOS|LogGWOnline|LogSocketSubsystemEOS: (Warning|Error)|LogEOS.*(Error|Warning)|Listening|LoadMap: EOS|Welcomed by server|Join succeeded|NetworkFailure|TravelFailure|GW: round \d+ started|GW: round over' |
    Select-Object -First 16 | ForEach-Object { $l = $_.Line; $i = $l.IndexOf(']Log'); $t = if ($i -ge 0) { $l.Substring($i + 1) } else { $l }; if ($t.Length -gt 170) { $t.Substring(0, 170) } else { $t } }
}
