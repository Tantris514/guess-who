# Starts the shared GuessWho editor (no rendering, MCP on 127.0.0.1:8010, Python remote exec on loopback).
# Does nothing if an UnrealEditor process is already running. Usage: powershell -File start_editor.ps1 [-Render]
param([switch]$Render)
$running = Get-Process UnrealEditor -ErrorAction SilentlyContinue
if ($running) { "editor already running (pid $($running.Id -join ','))"; exit 0 }
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$args = @("`"$uproject`"", '-unattended', '-nosplash', '-nosound', '-NoLiveCoding', '-log')
if ($Render) {
  # keep the viewport rendering at full rate while the window is in the background (screenshot QA)
  $args += '-ini:EditorSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False'
} else { $args += '-nullrhi' }
$p = Start-Process -FilePath $editor -ArgumentList $args -PassThru
$deadline = (Get-Date).AddMinutes(6)
while ((Get-Date) -lt $deadline -and -not $p.HasExited) {
  if (Get-NetTCPConnection -State Listen -LocalPort 8010 -ErrorAction SilentlyContinue) { "editor up (pid $($p.Id))"; exit 0 }
  Start-Sleep -Seconds 3
}
"editor did not come up"; exit 1
