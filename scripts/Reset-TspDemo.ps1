param([string]$Origin = 'http://127.0.0.1:8000')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
# Use the ignored local token without printing it or embedding it in command arguments.
$line = Get-Content -LiteralPath (Join-Path $root '.env') | Where-Object { $_.StartsWith('COORDINATOR_TOKEN=') }
if (!$line) { throw 'Configure the local coordinator token first.' }
$token = ($line -replace '^COORDINATOR_TOKEN=', '').Trim().Trim('"').Trim("'")
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$result = Invoke-RestMethod -Method Post -Uri ($Origin.TrimEnd('/') + '/api/v1/tsp/demo/reset') -Headers @{ Authorization = 'Bearer ' + $token } -WebSession $session
$result | Select-Object status, anchor, patients, clock | ConvertTo-Json -Depth 3
