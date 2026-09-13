$ErrorActionPreference = 'Stop'
$bridgeRoot = Join-Path $PSScriptRoot 'integrations/whatsapp-mcp/whatsapp-bridge'
$executable = (Resolve-Path (Join-Path $bridgeRoot 'whatsapp-bridge.exe')).Path
$pidFile = Join-Path $PSScriptRoot 'logs/whatsapp-bridge.pid'
if (Test-Path -LiteralPath $pidFile) {
    $bridgeId = [int](Get-Content -LiteralPath $pidFile)
    $existing = Get-Process -Id $bridgeId -ErrorAction SilentlyContinue
    if ($existing) {
        if ($existing.Path -ne $executable) { throw 'PID does not belong to this project bridge; refusing to stop it.' }
        Stop-Process -Id $bridgeId
        $existing.WaitForExit(10000) | Out-Null
    }
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outFile = Join-Path $PSScriptRoot "logs/bridge-$stamp.log"
$errFile = Join-Path $PSScriptRoot "logs/bridge-$stamp-error.log"
$started = Start-Process -FilePath $executable -WorkingDirectory $bridgeRoot -WindowStyle Hidden -RedirectStandardOutput $outFile -RedirectStandardError $errFile -PassThru
$started.Id | Set-Content -LiteralPath $pidFile
$outFile | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'logs/bridge-current-path.txt')
Write-Output "Started project bridge process $($started.Id)"
