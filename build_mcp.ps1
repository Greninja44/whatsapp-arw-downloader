param([switch]$Test)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$env:CGO_ENABLED = '1'
$env:CC = (Join-Path $projectRoot 'toolchain/zig-x86_64-windows-0.14.1/zig.exe') + ' cc'
$env:GOCACHE = Join-Path $projectRoot 'toolchain/go-cache'
$env:GOMODCACHE = Join-Path $projectRoot 'toolchain/go-mod'
Push-Location (Join-Path $projectRoot 'integrations/whatsapp-mcp/whatsapp-bridge')
try {
    if ($Test) {
        & (Join-Path $projectRoot 'toolchain/go/bin/go.exe') test -mod=mod .
    } else {
        & (Join-Path $projectRoot 'toolchain/go/bin/go.exe') build -mod=mod -o whatsapp-bridge.exe .
    }
    if ($LASTEXITCODE -ne 0) { throw 'Bridge compilation failed' }
} finally { Pop-Location }
