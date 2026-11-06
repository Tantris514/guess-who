# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File Tools\build_now.ps1   (build manager; the user asks, we build at once)
# Build manager: build as soon as the editor script running right now ends.
# 1. wait until no python editor script runs (ue_run / ue_main / ue_py); 2. post LOCK BUILD (new ue_run / run.sh calls
# wait on it); 3. wait for any script that started before the lock; 4. package.ps1; 5. UNLOCK BUILD.
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$locks = "$root\Tools\agent_logs\locks.md"
function Scripts([datetime]$before) {
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -like 'python*' -and $_.CommandLine -match 'ue_run\.py|ue_main\.py|ue_py\.py|ue_py_gp\.py' -and
        (-not $before -or $_.CreationDate -lt $before) })
}
$deadline = (Get-Date).AddMinutes(20)
while ((Scripts).Count -gt 0 -or (Get-Process -Name 'UnrealGame', 'GuessWho' -ErrorAction SilentlyContinue)) {
    if ((Get-Date) -gt $deadline) { 'gave up: an editor script or the game kept running for 20 min'; exit 1 }
    Start-Sleep -Seconds 3
}
$t0 = Get-Date
Add-Content $locks ("LOCK BUILD build-manager " + $t0.ToString('HH:mm') + ' — cook in progress: do not save any /Game asset until UNLOCK BUILD') -Encoding utf8
"LOCK BUILD at $($t0.ToString('HH:mm:ss'))"
try {
    $deadline = (Get-Date).AddMinutes(10)
    while ((Scripts $t0).Count -gt 0) {
        if ((Get-Date) -gt $deadline) { throw 'a script started before the lock is still running after 10 min' }
        Start-Sleep -Seconds 3
    }
    "cook starts $(Get-Date -Format 'HH:mm:ss')"
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\package.ps1"
    $ok = $LASTEXITCODE -eq 0
} finally {
    Add-Content $locks ("UNLOCK BUILD build-manager " + (Get-Date -Format 'HH:mm') + ' — build ' + (Get-Date -Format 'HH:mm') + ' done (Build\Windows)') -Encoding utf8
}
if (Test-Path "$root\Build\Windows\BUILD_INFO.txt") { Get-Content "$root\Build\Windows\BUILD_INFO.txt" -TotalCount 2 }
"result: " + $(if ($ok) { 'BUILD OK' } else { 'BUILD FAILED' })
