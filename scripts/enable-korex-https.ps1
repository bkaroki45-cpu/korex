# Run this script from an elevated PowerShell window (Run as Administrator).
$ErrorActionPreference = 'Stop'

$admin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    throw 'Administrator privileges are required. Open PowerShell with Run as Administrator, then run this script again.'
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$ruleName = 'KOREX Django HTTPS Outbound'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "KOREX virtual-environment Python was not found at: $pythonPath"
}

Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $ruleName -Direction Outbound -Program $pythonPath -Action Allow -Protocol TCP -RemotePort 443 -Profile Any | Out-Null

& $pythonPath -c "from urllib.request import urlopen; print(urlopen('https://api.coingecko.com/api/v3/ping', timeout=10).read().decode())"
Write-Host 'KOREX outbound HTTPS is configured and verified.' -ForegroundColor Green
