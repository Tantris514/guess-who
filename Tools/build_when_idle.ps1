# Packaged build as soon as the game is closed (archiving fails while Build\Windows is in use), with the shared
# LOCK BUILD / UNLOCK BUILD lines in Tools\agent_logs\locks.md so nobody saves /Game assets during the cook.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File Tools\build_when_idle.ps1 [-Who coordinator] [-MaxWaitMin 240]
param([string]$Who = 'coordinator', [int]$MaxWaitMin = 240)
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$locks = "$root\Tools\agent_logs\locks.md"
$deadline = (Get-Date).AddMinutes($MaxWaitMin)
function Busy {
    # an editor script (ue_run / ue_main / ue_py) saves assets: never start a cook in the middle of one
    $py = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'ue_run\.py|ue_main\.py|ue_py\.py|update_level\.sh' }
    return [bool]$py
}
while ((Get-Process -Name 'UnrealGame', 'GuessWho' -ErrorAction SilentlyContinue) -or (Busy) -or
       ((Get-Content $locks -Tail 5 | Select-String 'BUILD' | Select-Object -Last 1) -match 'LOCK BUILD' -and
        -not ((Get-Content $locks -Tail 5 | Select-String 'BUILD' | Select-Object -Last 1) -match 'UNLOCK BUILD'))) {
    if ((Get-Date) -gt $deadline) { "gave up: the game (or another build) was still running after $MaxWaitMin min"; exit 1 }
    Start-Sleep -Seconds 20
}
Add-Content $locks ("LOCK BUILD $Who " + (Get-Date -Format 'HH:mm') + ' — cook in progress: do not save any /Game asset until UNLOCK BUILD') -Encoding utf8
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\package.ps1"
    $ok = $LASTEXITCODE -eq 0
} finally {
    Add-Content $locks ("UNLOCK BUILD $Who " + (Get-Date -Format 'HH:mm') + ' — build ' + (Get-Date -Format 'HH:mm') + ' done (Build\Windows)') -Encoding utf8
}
if (Test-Path "$root\Build\Windows\BUILD_INFO.txt") { Get-Content "$root\Build\Windows\BUILD_INFO.txt" -TotalCount 2 }
"result: " + $(if ($ok) { 'BUILD OK' } else { 'BUILD FAILED' })
