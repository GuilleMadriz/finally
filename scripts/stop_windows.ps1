# Stop and remove the FinAlly container. The named volume is preserved.
# Usage: .\scripts\stop_windows.ps1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$Container = 'finally-app'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker CLI not found."
    exit 1
}

$Existing = docker ps -a --format '{{.Names}}'
if ($Existing -split "`n" | Where-Object { $_ -eq $Container }) {
    docker rm -f $Container | Out-Null
    Write-Host "Stopped $Container. Data volume 'finally-data' preserved."
} else {
    Write-Host "No $Container container running."
}
