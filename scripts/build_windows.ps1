$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($env:OS -ne 'Windows_NT') { throw 'Build on Windows x64 with Python 3.12.' }
$dirty = git status --porcelain
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'Use a clean committed Git checkout.' }
python -c "import sys; assert sys.version_info[:2] == (3,12)"
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 required' }
$version = python -c "from inventory import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0) { throw 'Version read failed' }
$archive = "dist/Inventory-$version-Windows-x64-test-candidate.zip"
if (Test-Path $archive) { throw 'Version artifact already exists; do not replace it.' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Core checks failed' }
python -m unittest discover -s tests_gui -v
if ($LASTEXITCODE -ne 0) { throw 'GUI checks failed' }
foreach ($script in @('check_source', 'fault_checks', 'performance')) {
    python "scripts/$script.py"
    if ($LASTEXITCODE -ne 0) { throw "$script failed" }
}
python -m PyInstaller --noconfirm --clean --windowed --onedir --name DroneLabInventory run_inventory.py
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
$exe = Join-Path (Get-Location) 'dist/DroneLabInventory/DroneLabInventory.exe'
$probe = Join-Path $env:TEMP ('inventory-probe-' + [guid]::NewGuid().ToString() + '.txt')
$process = Start-Process -FilePath $exe -ArgumentList @('--self-test','--self-test-file',('"{0}"' -f $probe)) -PassThru
if (-not $process.WaitForExit(30000)) { $process.Kill(); throw 'Bundled probe timed out' }
if ($process.ExitCode -ne 0 -or -not (Test-Path $probe)) { throw 'Bundled self-test failed' }
Get-Content $probe
Remove-Item $probe
Copy-Item docs dist/DroneLabInventory/docs -Recurse
Copy-Item CHANGELOG.md dist/DroneLabInventory/
Copy-Item README.md dist/DroneLabInventory/docs/SOURCE-README.md
$source = git rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Source commit read failed' }
@{version=$version; source_commit=$source; schema=2; tier='private Windows test candidate'; scanner_hil='BLOCKED'; legacy_migration='BLOCKED'; signing='unsigned'} | ConvertTo-Json | Set-Content dist/DroneLabInventory/build-manifest.json
@"
Inventory $version - rebuilt private Windows test candidate
Extract the entire ZIP and double-click DroneLabInventory.exe.
Python is bundled. Keep _internal beside the EXE.
USB HID keyboard scanner + Enter suffix. F2 focuses the scan field.
Data: %LOCALAPPDATA%\DroneLabInventory\inventory-v2.sqlite3
Earlier databases are retained separately; schema-1 migration is unsupported.
Make and verify a backup before upgrade. See docs for recovery/rollback.
Unsigned candidate: target-PC and scanner HIL validation remain required.
Source commit: $source
"@ | Set-Content dist/DroneLabInventory/README.txt
Compress-Archive -Path dist/DroneLabInventory -DestinationPath $archive
$hash = Get-FileHash $archive -Algorithm SHA256
($hash.Hash.ToLower() + "  Inventory-$version-Windows-x64-test-candidate.zip") | Set-Content "dist/Inventory-$version-Windows-x64-SHA256.txt"
$hash | Format-List
