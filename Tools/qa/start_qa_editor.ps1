# Second, RENDERED editor instance for screenshot QA, isolated from the shared headless editor:
#   - its Python remote execution uses multicast group 239.0.0.1:6767 (agents use 6766, so they never reach it)
#   - its MCP server is not started (the shared editor owns port 8010)
# It must never save anything. Usage: powershell -File start_qa_editor.ps1 [-ResX 1600 -ResY 900]
param([int]$ResX = 1600, [int]$ResY = 900)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$log = "J:\Projets\Unreal_Projects\Guess Who\Tools\qa\qa_editor.log"
$args = @(
  "`"$uproject`"", "-nosplash", "-unattended", "-nosound", "-NoLiveCoding", "-log", "-abslog=`"$log`"",
  "-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:RemoteExecutionMulticastGroupEndpoint=239.0.0.1:6767",
  "-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False",
  "-ini:EditorSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False",   # keep rendering in the background
  "-WinX=0", "-WinY=0", "-ResX=$ResX", "-ResY=$ResY"
)
$p = Start-Process -FilePath $editor -ArgumentList $args -PassThru
"qa editor pid $($p.Id), log $log"
