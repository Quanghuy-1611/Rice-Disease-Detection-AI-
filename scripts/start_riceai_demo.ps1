$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$apiRoot = Join-Path $projectRoot 'backend'
$webRoot = Join-Path $projectRoot 'frontend'
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$viteScript = Join-Path $webRoot 'node_modules\vite\bin\vite.js'
$webBuild = Join-Path $webRoot 'dist\index.html'

if (-not (Test-Path -LiteralPath $pythonExe)) {
  throw "Python environment missing: $pythonExe"
}
if (-not (Test-Path -LiteralPath $viteScript)) {
  throw "Web dependencies missing: $viteScript"
}
if (-not (Test-Path -LiteralPath $webBuild)) {
  throw "Web build missing: $webBuild"
}

function Test-RiceAiUrl([string]$url, [int]$timeoutSeconds = 3) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec $timeoutSeconds
    return $response.StatusCode -eq 200
  } catch {
    return $false
  }
}

function Wait-RiceAiModels {
  for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
      $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8015/api/health' -TimeoutSec 3
      if ($health.status -eq 'ok' -and $health.model_ready -and $health.plus_model_ready) {
        Write-Host 'Basic and Plus models are ready.' -ForegroundColor Green
        return
      }
    } catch {
      # The API might still be loading its models.
    }
    Start-Sleep -Seconds 1
  }
  throw 'API responded, but the Basic or Plus model is not ready. Check backend/server-8015.err.log.'
}

function Test-RiceAiPort([int]$port) {
  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $attempt = $client.BeginConnect('127.0.0.1', $port, $null, $null)
    return $attempt.AsyncWaitHandle.WaitOne(500) -and $client.Connected
  } catch {
    return $false
  } finally {
    $client.Dispose()
  }
}

function Wait-RiceAiUrl([string]$url, [string]$name) {
  for ($attempt = 0; $attempt -lt 50; $attempt++) {
    if (Test-RiceAiUrl $url) {
      Write-Host "$name is ready." -ForegroundColor Green
      return
    }
    Start-Sleep -Seconds 1
  }
  throw "$name did not start. Check server log files in backend/ or frontend/."
}

$apiHealth = 'http://127.0.0.1:8015/api/health'
Write-Host 'Checking RiceAI API...' -ForegroundColor Cyan
if (Test-RiceAiUrl $apiHealth) {
  Write-Host 'API is already running.' -ForegroundColor Green
} else {
  if (Test-RiceAiPort 8015) {
    throw 'Port 8015 is in use by another service. API was not started.'
  }
  Start-Process -FilePath $pythonExe `
    -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8015') `
    -WorkingDirectory $apiRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $apiRoot 'server-8015.out.log') `
    -RedirectStandardError (Join-Path $apiRoot 'server-8015.err.log') | Out-Null
  Write-Host 'Starting API. This can take up to 50 seconds...' -ForegroundColor Cyan
  Wait-RiceAiUrl $apiHealth 'API'
}
Wait-RiceAiModels

$webUrl = 'http://127.0.0.1:5174/'
Write-Host 'Checking RiceAI web...' -ForegroundColor Cyan
if (Test-RiceAiUrl $webUrl) {
  Write-Host 'Web is already running.' -ForegroundColor Green
} else {
  if (Test-RiceAiPort 5174) {
    throw 'Port 5174 is in use by another service. Web was not started.'
  }
  $nodeExe = (Get-Command node.exe -ErrorAction Stop).Source
  Start-Process -FilePath $nodeExe `
    -ArgumentList @('node_modules/vite/bin/vite.js', 'preview', '--host', '0.0.0.0', '--port', '5174', '--strictPort') `
    -WorkingDirectory $webRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $webRoot 'server-5174.out.log') `
    -RedirectStandardError (Join-Path $webRoot 'server-5174.err.log') | Out-Null
  Write-Host 'Starting web...' -ForegroundColor Cyan
  Wait-RiceAiUrl $webUrl 'Web'
}

$lanAddresses = Get-NetIPConfiguration |
  Where-Object { $_.NetAdapter.Status -eq 'Up' -and $_.IPv4DefaultGateway -and $_.IPv4Address } |
  ForEach-Object { $_.IPv4Address.IPAddress } |
  Select-Object -Unique

Write-Host ''
Write-Host 'RiceAI is ready on this laptop:' -ForegroundColor Green
Write-Host "  Web: $webUrl"
Write-Host "  API: http://127.0.0.1:8015/docs"
foreach ($address in $lanAddresses) {
  $lanUrl = "http://${address}:8015"
  if (Test-RiceAiUrl "$lanUrl/api/health") {
    Write-Host "  Phone API: $lanUrl/docs (laptop check OK)"
  } else {
    Write-Warning "Phone API did not respond at $lanUrl. Check the laptop network and firewall."
  }
}
$tailscaleExe = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'
if (Test-Path -LiteralPath $tailscaleExe) {
  $serveStatus = @()
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    # Tailscale being stopped is optional, not a RiceAI startup failure.
    $ErrorActionPreference = 'Continue'
    $serveStatus = & $tailscaleExe serve status 2>$null
    if ($LASTEXITCODE -ne 0) { $serveStatus = @() }
  } catch {
    $serveStatus = @()
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  $internetUrl = $serveStatus | Select-String -Pattern '^https://\S+' | Select-Object -First 1
  if ($internetUrl) {
    $tailscaleUrl = $internetUrl.Matches[0].Value
    if (Test-RiceAiUrl "$tailscaleUrl/api/health" 8) {
      Write-Host "  Tailscale API: $tailscaleUrl/docs (laptop check OK)"
    } else {
      Write-Warning "Tailscale API did not respond at $tailscaleUrl. Check Tailscale Serve."
    }
  } else {
    Write-Host '  Tailscale: off or not configured. Local RiceAI is still ready.' -ForegroundColor Yellow
  }
}
Write-Host 'Keep this laptop powered on while using RiceAI on a phone.'
Write-Host 'Laptop checks cannot verify the phone connection. Open the chosen API /docs address in the phone browser.'
Write-Host 'For Tailscale access, both devices must be connected to the same tailnet.'
exit 0
