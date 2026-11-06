# 1080p performance capture on the PACKAGED game: a listen server on L_Manor with 30 NPCs, Épique quality,
# CSV profiler over the last frames. Usage: powershell -File perf_test.ps1 [-Seconds 90] [-Quality 3] [-Editor] [-Tag x]
# -Editor runs the uncooked project (editor binary in -game): slower in absolute terms, meant for A/B comparisons
# such as costume pieces vs generated characters (Tools/gameplay/s29_gen_chars.py clear | stress).
param([int]$Seconds = 90, [int]$Quality = 3, [switch]$Editor, [string]$Tag = "", [int]$NPCs = 0)
$root = "J:\Projets\Unreal_Projects\Guess Who\Build\Windows"
$exe = "$root\GuessWho.exe"
$csvDir = "$root\GuessWho\Saved\Profiling\CSV"
$log = "J:\Projets\Unreal_Projects\Guess Who\Tools\qa\pkg_logs\perf$Tag.log"
$pre = @()
if ($Editor) {
  $exe = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
  $csvDir = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\Saved\Profiling\CSV"
  $pre = @("`"J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject`"")
}
New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null
$before = @(Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | ForEach-Object FullName)
$cmds = "t.MaxFPS 0,r.VSync 0,scalability $Quality,CsvProfile Frames=2400"
# -ForceRes: without it, Windows display scaling shrinks the window (1920x1080 became 1529x955).
$map = "/Game/GW/Maps/L_Manor?listen?Name=Perf"; if ($NPCs -gt 0) { $map += "?NPCs=$NPCs" }
$args = $pre + @($map, "-windowed", "-ResX=1920", "-ResY=1080", "-ForceRes", "-WinX=0", "-WinY=0", "-nosound",
          "-unattended", "-log", "-abslog=`"$log`"", "-ExecCmds=`"$cmds`"")
if ($Editor) { $args += @("-game", "-NoLiveCoding") }
$p = Start-Process -FilePath $exe -ArgumentList $args -PassThru
Start-Sleep -Seconds $Seconds
if ($Editor) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
else { Get-Process | Where-Object { $_.Path -like "$root\*" } | Stop-Process -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2
$csv = Get-ChildItem $csvDir -Filter *.csv -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.FullName } |
       Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $csv) { "no CSV written (see $log)"; exit 1 }
"csv: $($csv.FullName)"
Select-String $log -Pattern "Resolution changed to|SetRes|Viewport.*Size|ResolutionSizeX" | Select-Object -Last 3 | ForEach-Object { $_.Line }
& "V:\ComfyUI\ComfyUI\standalone-env\python.exe" -I -c @"
import csv, statistics, sys
rows = list(csv.DictReader(open(r'$($csv.FullName)', encoding='utf-8', errors='ignore')))
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None
rows = [r for r in rows if num(r.get('FrameTime')) is not None][-1200:]   # skip loading frames and the trailing header/metadata rows
def col(name):
    v = [num(r.get(name)) for r in rows]
    v = [x for x in v if x is not None]
    if not v: return None
    v.sort(); return (statistics.mean(v), v[int(len(v) * 0.95) - 1], len(v))
for name in ('FrameTime', 'GameThreadTime', 'RenderThreadTime', 'GPUTime'):
    c = col(name)
    if c: print(f'{name:18s} mean {c[0]:6.2f} ms   p95 {c[1]:6.2f} ms   (n={c[2]})')
ft = col('FrameTime')
if ft: print(f'FPS mean {1000/ft[0]:.0f}  (p95 frame -> {1000/ft[1]:.0f} fps)')
"@
