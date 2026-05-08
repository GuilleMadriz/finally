# Build the frontend (if needed), build the image (if needed), and run the container.
# Usage: .\scripts\start_windows.ps1 [-Build] [-Open]
[CmdletBinding()]
param(
    [switch]$Build,
    [switch]$Open
)

$ErrorActionPreference = 'Stop'

$Image = 'finally:latest'
$Container = 'finally-app'
$Volume = 'finally-data'
$Port = 8000

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$FrontendDir = Join-Path $RootDir 'frontend'
$OutDir = Join-Path $FrontendDir 'out'
$IndexHtml = Join-Path $OutDir 'index.html'

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker CLI not found. Install Docker Desktop and ensure 'docker' is on PATH."
    exit 1
}

# Decide whether the frontend needs (re)building.
$NeedFrontendBuild = $false
if (-not (Test-Path $IndexHtml) -or -not (Test-Path (Join-Path $OutDir '_next'))) {
    $NeedFrontendBuild = $true
} elseif ($Build.IsPresent) {
    $NeedFrontendBuild = $true
} else {
    $IndexMtime = (Get-Item $IndexHtml).LastWriteTimeUtc
    $WatchedRoots = @(
        (Join-Path $FrontendDir 'app'),
        (Join-Path $FrontendDir 'components'),
        (Join-Path $FrontendDir 'lib'),
        (Join-Path $FrontendDir 'package.json'),
        (Join-Path $FrontendDir 'package-lock.json'),
        (Join-Path $FrontendDir 'next.config.mjs'),
        (Join-Path $FrontendDir 'postcss.config.mjs')
    ) | Where-Object { Test-Path $_ }
    foreach ($root in $WatchedRoots) {
        $newer = Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTimeUtc -gt $IndexMtime } |
            Select-Object -First 1
        if ($newer) {
            $NeedFrontendBuild = $true
            break
        }
    }
}

if ($NeedFrontendBuild) {
    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        Write-Error "npm not found. Install Node 20+ (https://nodejs.org/) and re-run this script."
        exit 1
    }
    Write-Host "Building frontend (npm ci + npm run build)..."
    Push-Location $FrontendDir
    try {
        npm ci
        if (-not $?) { exit 1 }
        npm run build
        if (-not $?) { exit 1 }
    } finally {
        Pop-Location
    }
}

$NeedImageBuild = $Build.IsPresent
if (-not $NeedImageBuild) {
    docker image inspect $Image > $null 2>&1
    if (-not $?) { $NeedImageBuild = $true }
}

if ($NeedImageBuild) {
    Write-Host "Building image $Image..."
    docker build -t $Image $RootDir
    if (-not $?) { exit 1 }
}

$EnvArgs = @()
$EnvFile = Join-Path $RootDir '.env'
if (Test-Path $EnvFile) {
    $EnvArgs += @('--env-file', $EnvFile)
} else {
    Write-Host "Note: $EnvFile not found. Continuing without --env-file."
    Write-Host "      Copy .env.example to .env to enable LLM chat / Massive market data."
}

$Existing = docker ps -a --format '{{.Names}}'
if ($Existing -split "`n" | Where-Object { $_ -eq $Container }) {
    Write-Host "Removing existing container $Container..."
    docker rm -f $Container | Out-Null
}

Write-Host "Starting $Container..."
$RunArgs = @('run', '-d', '--name', $Container, '-p', "$($Port):8000", '-v', "$($Volume):/app/db") + $EnvArgs + @($Image)
docker @RunArgs | Out-Null
if (-not $?) { exit 1 }

$Url = "http://localhost:$Port"
Write-Host "FinAlly is running at $Url"
Write-Host "Logs: docker logs -f $Container"
Write-Host "Stop: .\scripts\stop_windows.ps1"

if ($Open.IsPresent) {
    Start-Process $Url
}
