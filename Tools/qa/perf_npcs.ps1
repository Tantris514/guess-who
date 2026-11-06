# Rendered frame times for several NPC counts (editor -game, uncooked: slower than a packaged build, use it to compare).
# One GAMETEST lock around each run; stops at once if the user starts playing (UnrealGame). Usage: perf_npcs.ps1 [-Counts 30,60,100,150]
param([string]$Counts = "30,60,100,150", [int]$Seconds = 100)
$root = "J:\Projets\Unreal_Projects\Guess Who"
$locks = "$root\Tools\agent_logs\locks.md"
foreach ($n in ($Counts -split ',')) {
  while ($true) {
    if (Get-Process UnrealGame -ErrorAction SilentlyContinue) { "the user is playing: stopped"; exit 3 }
    python -I -X utf8 "$root\Tools\qa\locks_open.py" --quiet
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 10
  }
  Add-Content $locks "LOCK GAMETEST events $(Get-Date -Format HH:mm) (rendered perf, $n NPCs)" -Encoding utf8
  "=== $n NPCs"
  & powershell -NoProfile -File "$root\Tools\qa\perf_test.ps1" -Editor -NPCs ([int]$n) -Seconds $Seconds -Tag "npc$n"
  Add-Content $locks "UNLOCK GAMETEST events $(Get-Date -Format HH:mm)" -Encoding utf8
  $log = "$root\Tools\qa\pkg_logs\perfnpc$n.log"
  "options: " + ((Select-String -Path $log -Pattern 'GW: options').Line | Select-Object -Last 1)
}
