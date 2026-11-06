# s40 inventory test, headless, one host: -GWInvTest steps (BP_GW_PlayerController.InvTestTick). Caller keeps LOCK GAMETEST open.
param([int]$Seconds = 110, [string]$Tag = "inv", [switch]$Render)
$editor = "J:\Projets\Unreal_Projects\Guess Who\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
$uproject = "J:\Projets\Unreal_Projects\Guess Who\GuessWho\GuessWho.uproject"
$log = "J:\Projets\Unreal_Projects\Guess Who\Tools\gameplay\logs\s40_$Tag.log"
Remove-Item $log -ErrorAction SilentlyContinue
$rhi = if ($Render) { @('-windowed', '-ResX=1600', '-ResY=900', '-ForceRes') } else { @('-nullrhi') }
$a = @("`"$uproject`"", "/Game/GW/Maps/L_Manor?listen?Name=Hote", '-game') + $rhi + @('-nosound', '-unattended', '-nosplash', '-NoLiveCoding', '-log', '-NoVerifyGC', '-GWDev', '-GWName=Hote', '-GWInvTest', '-GWViewLog', "-abslog=`"$log`"", '-port=7793')
$p = if ($Render) { Start-Process -FilePath $editor -ArgumentList $a -PassThru } else { Start-Process -FilePath $editor -ArgumentList $a -PassThru -WindowStyle Minimized }
$end = (Get-Date).AddSeconds(240)
while ((Get-Date) -lt $end -and -not $p.HasExited) {
  Start-Sleep -Seconds 4
  if ((Test-Path $log) -and (Select-String -Path $log -Pattern "GW invtest done" -Quiet)) { Start-Sleep -Seconds 3; break }
}
if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force }
"log: $log"
