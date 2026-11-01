# Real NetSPI MicroBurst Execution Harness
# Runs authentic PowerShell modules from tools/microburst/

$ErrorActionPreference = "Continue"
$projectRoot = Split-Path -Parent $PSScriptRoot
$microburstDir = Join-Path $projectRoot "tools\microburst"
$reportsDir = Join-Path $projectRoot "reports"

if (-not (Test-Path $reportsDir)) {
    New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " [NETSPI MICROBURST] Genuine PowerShell Security Execution" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Import Misc module directly
$miscModule = Join-Path $microburstDir "Misc\MicroBurst-Misc.psm1"
Write-Host "[+] Importing Module: $miscModule"
Import-Module $miscModule -Force

# 2. Execute Invoke-EnumerateAzureBlobs with Base name 'churnguard'
Write-Host "[+] Executing Invoke-EnumerateAzureBlobs for 'churnguard'..."
$blobEnumScript = Join-Path $microburstDir "Misc\Invoke-EnumerateAzureBlobs.ps1"
. $blobEnumScript

$outputFile = Join-Path $reportsDir "microburst_real_blobs_report.txt"
$results = Invoke-EnumerateAzureBlobs -Base "churnguard" -Verbose *>&1

$results | Out-File -FilePath $outputFile -Encoding utf8
Write-Host "[+] MicroBurst Execution Output saved to: $outputFile" -ForegroundColor Green
Write-Host "[+] Sample lines from real execution:"
Get-Content $outputFile -Head 15
Write-Host "============================================================" -ForegroundColor Cyan
