# Compile the C++ module (Source/GuessWho, EOS code games). -Editor also builds the editor target: the shared editor must be closed.
param([switch]$Editor)
$u = 'J:\Projets\Unreal_Projects\Guess Who'
$targets = @('GuessWho')
if ($Editor) { $targets += 'GuessWhoEditor' }
foreach ($t in $targets) {
  $cfg = 'Development'
  "== $t"
  & "$u\UE_5.8\Engine\Build\BatchFiles\Build.bat" $t Win64 $cfg "-Project=$u\GuessWho\GuessWho.uproject" -WaitMutex *>&1 |
    ForEach-Object { "$_" } | Select-String -Pattern 'error|Result:|Total execution|fatal' | Select-Object -First 30 | ForEach-Object { $_.Line }
}
