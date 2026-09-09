$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'

$python = Join-Path $PSScriptRoot 'model_benchmark\.venv312\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Khong tim thay Python cua du an: $python"
}

& powershell.exe -ExecutionPolicy Bypass -File '.\FINAL_TEST_11CLASS_LARGE.ps1'
if ($LASTEXITCODE -ne 0) {
    throw "Final evaluation dung voi exit code $LASTEXITCODE."
}

& $python 'model_benchmark\src\compare_final_11class_large_v2.py'
if ($LASTEXITCODE -ne 0) {
    throw "Paired Macro-F1 comparison dung voi exit code $LASTEXITCODE. Predictions goc van duoc giu nguyen."
}

Write-Host 'Da test va so sanh thong ke nghiem ngat xong.' -ForegroundColor Green
