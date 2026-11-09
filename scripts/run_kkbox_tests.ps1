param([switch]$SkipSpark)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Missing .venv Python. Install requirements-kkbox.txt in Python 3.11 first.'
}

$javaCommand = Get-Command java.exe -ErrorAction Stop
$javaHomeResolved = Split-Path -Parent (Split-Path -Parent $javaCommand.Source)
if (-not (Test-Path -LiteralPath (Join-Path $javaHomeResolved 'bin\java.exe'))) {
    throw 'A working JDK is required for the Spark feature test.'
}

$env:JAVA_HOME = $javaHomeResolved
$env:SPARK_LOCAL_IP = '127.0.0.1'
$env:PYSPARK_PYTHON = $python
$env:PYSPARK_DRIVER_PYTHON = $python
$env:PYTHONPATH = $repoRoot

$testFiles = @(
    'tests/test_kkbox_api.py',
    'tests/test_kkbox_integrity.py',
    'tests/test_kkbox_figures.py',
    'tests/test_kkbox_benchmarks.py',
    'tests/test_kkbox_web.py'
)
if (-not $SkipSpark) {
    $testFiles += 'tests/test_kkbox_features.py'
}

Write-Host "KKBox tests using $($javaCommand.Source)"
Push-Location $repoRoot
try {
    & $python -m pytest @testFiles -q
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
