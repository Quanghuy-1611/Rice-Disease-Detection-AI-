$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'

$python = Join-Path $PSScriptRoot 'model_benchmark\.venv312\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Khong tim thay Python cua du an: $python"
}

& $python 'model_benchmark\src\final_evaluate_11class_large.py' `
    --unlock-test I_UNDERSTAND_TEST_IS_FINAL `
    --workers 2 `
    --device cuda

if ($LASTEXITCODE -ne 0) {
    throw "Final evaluation bi tu choi hoac gap loi voi exit code $LASTEXITCODE. Khong xoa/sua output de chay lai truoc khi kiem tra nguyen nhan."
}

Write-Host 'Da danh gia xong internal test va external test; hai ket qua duoc luu rieng.' -ForegroundColor Green
