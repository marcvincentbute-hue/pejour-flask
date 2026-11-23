param([Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference='Stop'
$sourceRoot=[IO.Path]::GetFullPath($PSScriptRoot)
$targetRoot=[IO.Path]::GetFullPath($Target)
if ($sourceRoot -eq $targetRoot) { throw 'Extract this update to a separate folder first.' }
if (-not (Test-Path -LiteralPath (Join-Path $targetRoot 'manage.py'))) { throw 'Target must be your existing Pejour Flask folder.' }
$blocked=@('.git','.venv','__pycache__','.pytest_cache','runtime','backups')
# Copy only public release files. Never overwrite .env, keys, local backups or environments.
foreach($file in Get-ChildItem -LiteralPath $sourceRoot -File -Recurse -Force) {
    $relative=$file.FullName.Substring($sourceRoot.Length).TrimStart([IO.Path]::DirectorySeparatorChar,[IO.Path]::AltDirectorySeparatorChar)
    $parts=$relative -split '[\\/]'
    if (@($parts | Where-Object { $_ -in $blocked }).Count -gt 0) { continue }
    if ($file.Name -like '.env*' -and $file.Name -ne '.env.example') { continue }
    if ($file.Extension -in @('.log','.pyc')) { continue }
    $destination=Join-Path $targetRoot $relative
    New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
}
Write-Host 'Updated source files. Your .env, virtual environment and database are preserved.'
$obsolete=Join-Path $targetRoot 'docs\seed.md'
if(Test-Path -LiteralPath $obsolete) { Remove-Item -LiteralPath $obsolete }
Set-Location -LiteralPath $targetRoot
& .\.venv\Scripts\python.exe manage.py upgrade
if($LASTEXITCODE -ne 0) { throw 'Upgrade did not finish. Stop the server and rerun: .\.venv\Scripts\python.exe manage.py upgrade' }
Write-Host 'Ready. Start your website again using .\start.ps1.'
