# BotMMO cleanup — junk only. Keeps source, tests, DB, .env*, docs.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$files = @(
  'Untitled-1.txt',
  'purge_services_private.py.py',
  'refactor.py',
  'test_binance_spot.py',
  'app\test_mbbank.py',
  'tests\_analyze_router.py',
  'tests\_extract_queries.py',
  'tests\_patch_storage.py',
  'admin_preview.err.log',
  'admin_preview.out.log',
  'bot.log',
  'bot.log.1',
  'bot.instance.lock',
  'backup_before_restore_20260625_210326.zip',
  'backup_before_restore_20260625_210548.zip',
  'backup_before_restore_20260702_001214.zip'
)

$n = 0
foreach ($rel in $files) {
  $p = Join-Path $root $rel
  if (Test-Path -LiteralPath $p) {
    Remove-Item -LiteralPath $p -Force
    Write-Host "DEL  $rel"
    $n++
  }
}

$rb = Join-Path $root 'runtime_backups'
if (Test-Path -LiteralPath $rb) {
  Remove-Item -LiteralPath $rb -Recurse -Force
  Write-Host 'DEL  runtime_backups/'
  $n++
}

Get-ChildItem (Join-Path $root 'app\handlers') -Filter 'data_*.json' -File -ErrorAction SilentlyContinue | ForEach-Object {
  Remove-Item -LiteralPath $_.FullName -Force
  Write-Host "DEL  app/handlers/$($_.Name)"
  $n++
}

Get-ChildItem $root -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue | ForEach-Object {
  Remove-Item -LiteralPath $_.FullName -Recurse -Force
  Write-Host "DEL  $($_.FullName.Substring($root.Length + 1))/"
  $n++
}

Write-Host ""
Write-Host "Done. Removed ~$n items."
Write-Host "Kept: database.sqlite, .env*, app source, real tests, docs."
Write-Host ""
Write-Host '--- root ---'
Get-ChildItem $root -Name
Write-Host '--- tests ---'
Get-ChildItem (Join-Path $root 'tests') -Name
Write-Host '--- handlers (no data_*.json expected) ---'
Get-ChildItem (Join-Path $root 'app\handlers') -Name
