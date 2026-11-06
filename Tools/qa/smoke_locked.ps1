# Build manager's smoke test of a packaged build folder, under the shared GAMETEST lock (Tools\agent_logs\locks.md):
# waits until no other LOCK GAMETEST is open and UDP 7777 is free, posts "LOCK GAMETEST build-manager", backs off if
# another agent's lock landed just before it, runs pkg_nettest.ps1 -BuildDir, and always posts "UNLOCK GAMETEST".
# Last line printed: "SMOKE OK: ..." / "SMOKE FAIL: ..." / "SMOKE SKIPPED: ...". Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File Tools\qa\smoke_locked.ps1 [-BuildDir <folder>] [-Seconds 150]
param([string]$BuildDir = "J:\Projets\Unreal_Projects\Guess Who\Build\Windows", [int]$Seconds = 150, [int]$MaxWaitMin = 30)
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$locks = "$root\Tools\agent_logs\locks.md"
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Post($l) { [IO.File]::AppendAllText($locks, "$l`r`n", $utf8) }
function GameTestLines { @(Get-Content $locks -ErrorAction SilentlyContinue | Where-Object { $_ -match '^(LOCK|UNLOCK) GAMETEST' }) }
function GameTestOpen { $g = GameTestLines; return ($g.Count -gt 0 -and $g[-1] -match '^LOCK GAMETEST') }
function PortBusy { [bool](Get-NetUDPEndpoint -LocalPort 7777 -ErrorAction SilentlyContinue) }

$deadline = (Get-Date).AddMinutes($MaxWaitMin)
while ($true) {
    while ((GameTestOpen) -or (PortBusy)) {
        if ((Get-Date) -gt $deadline) { "SMOKE SKIPPED: a GAMETEST lock or port 7777 stayed busy for $MaxWaitMin min"; exit 3 }
        Start-Sleep -Seconds 10
    }
    $mine = "LOCK GAMETEST build-manager $(Get-Date -Format 'HH:mm:ss') (smoke test of $(Split-Path (Split-Path $BuildDir) -Leaf)\$(Split-Path $BuildDir -Leaf), <= 4 min)"
    Post $mine
    Start-Sleep -Seconds 2
    $g = GameTestLines
    $i = [array]::LastIndexOf($g, $mine)
    if ($i -gt 0 -and $g[$i - 1] -match '^LOCK GAMETEST' -and $g[$i - 1] -notmatch 'build-manager') {
        # another agent locked first: release ours and re-post theirs so the last GAMETEST line still says it is held
        Post "UNLOCK GAMETEST build-manager $(Get-Date -Format 'HH:mm:ss') (backed off)"
        Post "$($g[$i - 1]) [re-posted by build-manager after a lock race]"
        Start-Sleep -Seconds 20
        continue
    }
    break
}
try {
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\qa\pkg_nettest.ps1" -Seconds $Seconds -BuildDir $BuildDir 2>&1 | Out-String
} finally {
    Post "UNLOCK GAMETEST build-manager $(Get-Date -Format 'HH:mm:ss')"
}
$out
$clean = ([regex]::Matches($out, 'Accessed None=0 BP runtime errors=0 Fatal=0')).Count -ge 2
$played = $out -match 'Join succeeded' -and $out -match 'round 2 started'
$voices = 0
if (Test-Path "$root\Tools\qa\pkg_logs\server.log") { $voices = @(Select-String -Path "$root\Tools\qa\pkg_logs\server.log" -Pattern 'GW: say|voice').Count }
$text = "server+client clean=$clean, joined+2 rounds=$played, voice cues=$voices"
if ($out -match 'port 7777 busy') { "SMOKE SKIPPED: $(([regex]::Match($out, 'port 7777 busy[^\r\n]*')).Value)"; exit 3 }
if ($clean -and $played) { "SMOKE OK: $text"; exit 0 } else { "SMOKE FAIL: $text"; exit 1 }
