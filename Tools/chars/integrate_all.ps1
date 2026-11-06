# Detached: rebuild the cast from the manifest (s29), then package. Log: AssetGen\chars\integrate_all.log
$root = 'J:\Projets\Unreal_Projects\Guess Who'
$py = 'V:\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe'
$log = "$root\AssetGen\chars\integrate_all.log"
function Say($m) { Add-Content $log ((Get-Date -Format 'HH:mm:ss') + ' ' + $m) -Encoding utf8 }
Say 'start editor'
& powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\start_editor.ps1" *>> $log
Say 's29'
& $py -I -X utf8 "$root\Tools\ui\ue_run.py" "$root\Tools\gameplay\s29_gen_chars.py" *>> $log
Say "s29 exit $LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { Say 'STOP: s29 failed, no build'; exit 1 }
Say 'build'
& powershell -NoProfile -ExecutionPolicy Bypass -File "$root\Tools\build_now.ps1" *>> $log
Say 'end'
