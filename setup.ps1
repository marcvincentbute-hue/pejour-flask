$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($pythonCommand) {
    & py -3 -m venv .venv
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand -or $pythonCommand.Source -like '*WindowsApps*') {
        throw 'Install Python 3.12 or newer from python.org, select Add Python to PATH, then reopen PowerShell.'
    }
    & python -m venv .venv
}
if ($LASTEXITCODE -ne 0) { throw 'Python environment could not be created.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your internet connection.' }
if (-not (Test-Path -LiteralPath '.env')) {
    & .\.venv\Scripts\python.exe manage.py setup-database
    if ($LASTEXITCODE -ne 0) { throw 'Database setup did not finish. Existing PHP files are unchanged.' }
}
Write-Host 'Setup complete. Add your Gmail App Password to .env, then run .\start.ps1.'
