param(
    [switch]$PostgreSQL,
    [ValidateSet('msedge', 'chromium')][string]$Browser = 'msedge'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$reportDir = Join-Path $root ('test-reports\' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$null = New-Item -ItemType Directory -Path $reportDir -Force
$previousPostgres = $env:TEST_POSTGRES_URL
$previousBrowser = $env:E2E_BROWSER_CHANNEL
$previousJson = $env:PLAYWRIGHT_JSON_OUTPUT_FILE
$results = [ordered]@{}
try {
    Push-Location (Join-Path $root 'backend')
    try {
        $env:TEST_POSTGRES_URL = $null
        & $python -m pytest -q --tb=short "--basetemp=$reportDir\sqlite" "--junitxml=$reportDir\sqlite.xml"
        $results['SQLite API'] = $LASTEXITCODE
        if ($PostgreSQL) {
            $env:TEST_POSTGRES_URL = (Get-Content -LiteralPath '../.env' | Where-Object { $_.StartsWith('DATABASE_URL=') }) -replace '^DATABASE_URL=', ''
            if (!$env:TEST_POSTGRES_URL.StartsWith('postgresql')) { throw 'Set a PostgreSQL DATABASE_URL in .env.' }
            & $python -m pytest -q --tb=short "--basetemp=$reportDir\postgres" "--junitxml=$reportDir\postgres.xml"
            $results['PostgreSQL API'] = $LASTEXITCODE
        }
    } finally { Pop-Location }

    Push-Location (Join-Path $root 'frontend')
    try {
        npm.cmd run build
        $results['TypeScript and Vite build'] = $LASTEXITCODE
        npm.cmd run test -- --reporter=default --reporter=junit "--outputFile.junit=$reportDir\components.xml"
        $results['React components'] = $LASTEXITCODE
        $env:E2E_BROWSER_CHANNEL = if ($Browser -eq 'msedge') { 'msedge' } else { $null }
        $env:PLAYWRIGHT_JSON_OUTPUT_FILE = Join-Path $reportDir 'browser.json'
        npm.cmd run test:e2e -- --reporter=line,json
        $results['Browser journey'] = $LASTEXITCODE
    } finally { Pop-Location }
} finally {
    $env:TEST_POSTGRES_URL = $previousPostgres
    $env:E2E_BROWSER_CHANNEL = $previousBrowser
    $env:PLAYWRIGHT_JSON_OUTPUT_FILE = $previousJson
    $results | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath (Join-Path $reportDir 'summary.json')
    Write-Host "Verification reports are in $reportDir"
}
if ($results.Values | Where-Object { $_ -ne 0 }) { throw 'One or more verification suites failed.' }
