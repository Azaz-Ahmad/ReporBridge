param([switch]$SQLite)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath '.env') { throw '.env already exists. Review it before changing database or token settings.' }
function New-DemoToken {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes)
}
$password = [guid]::NewGuid().ToString('N')
$database = "postgresql+psycopg://reprobridge:${password}@127.0.0.1:5432/reprobridge"
if ($SQLite) { $database = '' }
@(
    "DATABASE_URL=$database"
    "POSTGRES_PASSWORD=$password"
    "COORDINATOR_TOKEN=$(New-DemoToken)"
    "REVIEWER_TOKEN=$(New-DemoToken)"
    "VIEWER_TOKEN=$(New-DemoToken)"
) | Set-Content -Encoding ascii -LiteralPath '.env'
Write-Host 'Created .env. Use the role tokens from that local file to sign in.'
