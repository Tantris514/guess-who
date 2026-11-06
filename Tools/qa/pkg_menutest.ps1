# Menu flow on the PACKAGED game, through the real button handlers (WBP_MainMenu OnHostClicked / OnJoinClicked):
# instance 1 starts on the main menu with -GWMenuHost and must open L_Manor as a listen server; instance 2 starts on
# the main menu with -GWMenuJoin (empty IP field -> 127.0.0.1) and must be welcomed by it.
# Usage: powershell -File pkg_menutest.ps1 [-Seconds 75]
param([int]$Seconds = 75)
$root = "J:\Projets\Unreal_Projects\Guess Who\Build\Windows"
$exe = "$root\GuessWho.exe"
$logs = "J:\Projets\Unreal_Projects\Guess Who\Tools\qa\pkg_logs"
New-Item -ItemType Directory -Force $logs | Out-Null
Get-Process | Where-Object { $_.Path -like "$root\*" } | Stop-Process -Force -ErrorAction SilentlyContinue
$common = @("-windowed", "-ResX=960", "-ResY=540", "-ForceRes", "-nosound", "-unattended", "-log")
$h = Start-Process -FilePath $exe -ArgumentList ($common + @("-WinX=0", "-WinY=0", "-GWMenuHost", "-abslog=`"$logs\menu_host.log`"")) -PassThru
Start-Sleep -Seconds 25
$c = Start-Process -FilePath $exe -ArgumentList ($common + @("-WinX=980", "-WinY=0", "-GWMenuJoin", "-abslog=`"$logs\menu_join.log`"")) -PassThru
Start-Sleep -Seconds $Seconds
Get-Process | Where-Object { $_.Path -like "$root\*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
function Show($name, $patterns) {
  "--- $name"
  foreach ($p in $patterns.GetEnumerator()) {
    $m = @(Select-String -Path "$logs\$name" -Pattern $p.Value)
    "{0,-34} {1}" -f $p.Key, $(if ($m.Count) { "OK  ($($m.Count))  " + $m[0].Line.Substring([Math]::Max(0, $m[0].Line.Length - 110)) } else { "MISSING" })
  }
}
Show "menu_host.log" ([ordered]@{ "browse to the manor as listen" = "Browse: /Game/GW/Maps/L_Manor.*listen"; "manor loaded" = "LoadMap: /Game/GW/Maps/L_Manor";
  "game mode ready" = "GW: game mode ready"; "client joined" = "GW: player joined"; "bad console command" = "Command not recognized" })
Show "menu_join.log" ([ordered]@{ "connect to 127.0.0.1" = "Browse: 127\.0\.0\.1"; "welcomed by server" = "Welcomed by server"; "manor loaded" = "LoadMap: .*L_Manor";
  "connection failure" = "Connection failed|NetworkFailure|TravelFailure" })
foreach ($n in "menu_host.log", "menu_join.log") { "$n Accessed None: " + (Select-String -Path "$logs\$n" -Pattern 'Accessed None').Count + "  Script errors: " + (Select-String -Path "$logs\$n" -Pattern 'LogScript: Error|Blueprint Runtime Error').Count }
