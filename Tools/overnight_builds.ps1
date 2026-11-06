# Overnight builds (build manager): a packaged build every ~2.5 h when the game content changed, and a FINAL build at
# 10:00, smoke-tested before the user is up (~11:00). Build\Windows always holds a build that passed its smoke test:
#   1. wait until no game runs, no LOCK BUILD / LOCK HOOKS is open, open asset LOCKs are gone (at most 20 min);
#   2. wait for the editor script running now, post LOCK BUILD (ue_run.py and level/run.sh wait on it), wait for the
#      scripts that started before the lock;
#   3. package.ps1 into Build_next, UNLOCK BUILD; 4. Tools\qa\smoke_locked.ps1 on Build_next\Windows (GAMETEST lock,
#      port 7777 free); 5. only if it passed: Build\Windows -> Build\Windows_prev, Build_next\Windows -> Build\Windows.
# Every result goes to Tools\agent_logs\coordinator.md. Usage (runs until the final build is done):
#   powershell -NoProfile -ExecutionPolicy Bypass -File Tools\overnight_builds.ps1 -LastBuild '2026-11-02 21:08' -FinalAt '2026-11-03 10:00'
param([string]$LastBuild = '2026-11-03 07:11', [string]$FinalAt = '2026-11-03 10:00', [int]$EveryMin = 150)
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$locks = "$root\Tools\agent_logs\locks.md"
$coord = "$root\Tools\agent_logs\coordinator.md"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$last = [datetime]$LastBuild          # start of the last build that is in Build\Windows
$final = [datetime]$FinalAt

function Say($msg) { [IO.File]::AppendAllText($coord, "$(Get-Date -Format 'yyyy-MM-dd HH:mm') build-manager: $msg`r`n", $utf8); $msg }
function LockLine($msg) { [IO.File]::AppendAllText($locks, "$msg`r`n", $utf8) }
function Scripts($before) {
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -like 'python*' -and $_.CommandLine -match 'ue_run\.py|ue_main\.py|ue_py\.py|ue_py_gp\.py' -and
        (-not $before -or $_.CreationDate -lt $before) })
}
function Game { [bool](Get-Process -Name 'UnrealGame', 'GuessWho' -ErrorAction SilentlyContinue) }
# free commit memory in GB: a cook takes ~10 GB; below 15 GB free it could run the machine (and the agents) out of memory
function FreeCommitGB { [math]::Round((Get-CimInstance Win32_OperatingSystem).FreeVirtualMemory / 1MB, 1) }
function OpenKind($kind) {
    $l = Select-String -Path $locks -Pattern "^(LOCK|UNLOCK) $kind" -ErrorAction SilentlyContinue | Select-Object -Last 1
    return ($l -and $l.Line -match "^LOCK $kind")
}
function OpenAssetLocks {
    $open = @{}
    foreach ($l in (Get-Content $locks -ErrorAction SilentlyContinue)) {
        if ($l -match '^(LOCK|UNLOCK) (/Game/\S+)') { if ($Matches[1] -eq 'LOCK') { $open[$Matches[2]] = $l } else { $open.Remove($Matches[2]) } }
    }
    return @($open.Keys)
}
function Changed($since) {
    @(Get-ChildItem "$root\GuessWho\Content", "$root\GuessWho\Config" -Recurse -File -Include *.uasset, *.umap, *.ini -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -gt $since }).Count
}
function Smoke($dir) {
    # under the shared GAMETEST lock, with UDP 7777 free (Tools\qa\smoke_locked.ps1); a smoke test whose client joined
    # another agent's listen server failed the 07:11 build for nothing
    $out = & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\qa\smoke_locked.ps1" -BuildDir $dir 2>&1 | Out-String
    $res = ([regex]::Match($out, 'SMOKE (OK|FAIL|SKIPPED): [^\r\n]*')).Value
    if (-not $res) { $res = 'SMOKE FAIL: no result' }
    if ($out -match 'SMOKE FAIL' -and (Test-Path "$root\Tools\qa\pkg_logs")) {
        $keep = "$root\Tools\qa\pkg_logs\failed_$(Get-Date -Format 'HHmm')"
        New-Item -ItemType Directory -Force $keep | Out-Null
        Copy-Item "$root\Tools\qa\pkg_logs\server.log", "$root\Tools\qa\pkg_logs\client.log" $keep -ErrorAction SilentlyContinue
        $res += " (logs kept in $keep)"
    }
    return @{ ok = ($res -match '^SMOKE OK'); text = $res }
}

function Build($label) {
    # a game or another build blocks (40 min max); HOOKS / asset LOCK lines are waited for 20 min only (they are
    # sometimes left open), since what is cooked is what is saved on disk and no script runs during the cook
    $deadline = (Get-Date).AddMinutes(40)
    $softUntil = (Get-Date).AddMinutes(20)
    while ((Game) -or (OpenKind 'BUILD') -or (FreeCommitGB) -lt 15 -or (((OpenKind 'HOOKS') -or (OpenAssetLocks).Count -gt 0) -and (Get-Date) -lt $softUntil)) {
        if ((Get-Date) -gt $deadline) {
            return Say "$label build SKIPPED: no window in 40 min (game=$(Game) lockBuild=$(OpenKind 'BUILD') freeCommitGB=$(FreeCommitGB)); Build\Windows unchanged ($($last.ToString('HH:mm')))"
        }
        Start-Sleep -Seconds 5
    }
    $al = @(OpenAssetLocks) + $(if (OpenKind 'HOOKS') { @('HOOKS') } else { @() })
    $t0 = Get-Date
    # lock first (new ue_run / run.sh calls wait on it), then let the scripts already running finish
    LockLine "LOCK BUILD build-manager $($t0.ToString('HH:mm')) - cook in progress: do not save any /Game asset until UNLOCK BUILD"
    try {
        $scriptsUntil = (Get-Date).AddMinutes(20)
        while ((Scripts $t0).Count -gt 0) {
            if ((Get-Date) -gt $scriptsUntil) { throw "an editor script started before the lock still runs after 20 min" }
            Start-Sleep -Seconds 3
        }
        $next = "$root\Build_next"
        if (Test-Path $next) { Remove-Item $next -Recurse -Force }
        $pk = & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\package.ps1" -Out $next 2>&1 | Out-String
        $okPk = $LASTEXITCODE -eq 0 -and (Test-Path "$next\Windows\GuessWho.exe")
    } catch {
        $okPk = $false; $pk = "$_"
    } finally {
        LockLine "UNLOCK BUILD build-manager $(Get-Date -Format 'HH:mm') - $label cook done"
    }
    $logPath = ([regex]::Match("$pk", 'log: (.+?\.log)')).Groups[1].Value
    $errs = 0; $cooked = '?'
    if ($logPath -and (Test-Path $logPath)) {
        $txt = Get-Content $logPath
        $errs = @($txt | Select-String -Pattern 'LogCook: Error|LogBlueprint: Error|: Error:').Count
        $m = $txt | Select-String -Pattern 'Packages Cooked: (\d+)' | Select-Object -Last 1
        if ($m) { $cooked = $m.Matches[0].Groups[1].Value }
    }
    $note = $(if ($al.Count) { " (open LOCK lines ignored after 20 min: $($al -join ', '))" } else { '' })
    if (-not $okPk) { return Say "$label build FAILED at cook/package (errors=$errs, log $logPath)$note; Build\Windows unchanged ($($last.ToString('HH:mm')))" }
    # test the new build where it was made; only a build that passed replaces Build\Windows
    $s = Smoke "$next\Windows"
    if (-not $s.ok) {
        $bad = "$root\Build\Windows_failed_$($t0.ToString('HHmm'))"
        Move-Item "$next\Windows" $bad
        return Say "$label build $($t0.ToString('HH:mm')) cooked ($cooked packages, $errs errors) but did not pass its smoke test ($($s.text)); kept the previous build ($($last.ToString('HH:mm'))), new one in $bad$note"
    }
    while (Game) { Start-Sleep -Seconds 10 }
    $prev = "$root\Build\Windows_prev"
    if (Test-Path $prev) { Remove-Item $prev -Recurse -Force }
    Move-Item "$root\Build\Windows" $prev
    Move-Item "$next\Windows" "$root\Build\Windows"
    $script:last = $t0
    return Say "$label build $($t0.ToString('HH:mm')) OK: $cooked packages, $errs cook errors, smoke test passed ($($s.text)); in Build\Windows$note"
}

Say "overnight builds started: every ~$EveryMin min when content changed, final at $($final.ToString('HH:mm')); current Build\Windows = $($last.ToString('HH:mm'))"
$attempt = $last                      # time of the last build or check: the next one is $EveryMin later
while ($true) {
    $slot = $attempt.AddMinutes($EveryMin)
    if ($slot -lt (Get-Date)) { $slot = Get-Date }
    $isFinal = $slot.AddMinutes(60) -ge $final
    if ($isFinal) { $slot = $final }
    while ((Get-Date) -lt $slot) { Start-Sleep -Seconds 60 }
    $attempt = Get-Date
    $n = Changed $last
    if ($isFinal) {
        if ($n -gt 0) { Build 'FINAL' } else {
            $s = Smoke "$root\Build\Windows"
            Say "FINAL: no content change since $($last.ToString('HH:mm')); that build stays, smoke test again: $(if ($s.ok) { 'passed' } else { 'FAILED' }) ($($s.text))"
        }
        break
    }
    if ($n -gt 0) { Build 'scheduled' } else { Say "scheduled check: no content change since $($last.ToString('HH:mm')), no build" }
}
Say 'overnight builds finished'
