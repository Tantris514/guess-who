# Compile + cook + stage + pak + archive a Development Win64 build of GuessWho (C++ module Source/GuessWho for EOS code games).
# After changing Source/, rebuild the editor target too: Tools\online\build_code_targets.ps1 -Editor (editor closed).
# Usage: powershell -File package.ps1 [-Out "J:\Projets\Unreal_Projects\Guess Who\Build"]
# Runs at below-normal priority so ComfyUI and the editor keep the machine responsive.
param([string]$Out = "J:\Projets\Unreal_Projects\Guess Who\Build", [switch]$SkipCook)
$engine = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$logDir = "J:\Projets\Unreal_Projects\Guess Who\Tools\package_logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
(Get-Process -Id $PID).PriorityClass = "BelowNormal"   # inherited by UAT, the cooker and the shader workers
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$log = "$logDir\uat-$stamp.log"
$uatArgs = @(
  "BuildCookRun", "-project=`"$uproject`"", "-noP4", "-platform=Win64",
  "-clientconfig=Development", "-cook", "-map=/Game/GW/Maps/L_MainMenu+/Game/GW/Maps/L_Manor",
  "-build", "-stage", "-pak", "-prereqs", "-archive", "-archivedirectory=`"$Out`"",
  "-nocompileeditor", "-unattended", "-utf8output"
)
if ($SkipCook) { $uatArgs = $uatArgs | ForEach-Object { if ($_ -eq "-cook") { "-skipcook" } else { $_ } } }
"log: $log"
# the dev-only Python remote-exec config must not be staged: set it aside for the build, put it back after
$devIni = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\Config\UserEngine.ini"
$devCopy = "J:\Projets\Unreal_Projects\Guess Who\Tools\dev_config\UserEngine.ini"
$hadDev = Test-Path $devIni
if ($hadDev) { Remove-Item $devIni -Force }
try {
  & "$engine\Build\BatchFiles\RunUAT.bat" @uatArgs *> $log
  $code = $LASTEXITCODE
} finally {
  if ($hadDev) { Copy-Item $devCopy $devIni -Force }
}
"exit code: $code"
if ($code -eq 0) {
  Copy-Item "J:\Projets\Unreal_Projects\Guess Who\GUIDE_JOUEUR.md" "$Out\Windows\GUIDE_JOUEUR.md" -Force -ErrorAction SilentlyContinue
  "Build du $(Get-Date -Format 'yyyy-MM-dd HH:mm')`r`nJournal : $log" | Set-Content -Encoding utf8 "$Out\Windows\BUILD_INFO.txt"
}
Select-String -Path $log -Pattern "BUILD SUCCESSFUL|BUILD FAILED|AutomationTool exiting with ExitCode|Error:" | Select-Object -Last 15 | ForEach-Object { $_.Line }
exit $code
