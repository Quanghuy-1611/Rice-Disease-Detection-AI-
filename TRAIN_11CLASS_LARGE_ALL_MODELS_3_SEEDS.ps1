$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'

$python = Join-Path $PSScriptRoot 'model_benchmark\.venv312\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Khong tim thay Python cua du an: $python"
}

& $python 'model_benchmark\src\run_campaign_11class_large_continuous.py' --workers 2 --device cuda
if ($LASTEXITCODE -ne 0) {
    throw "Campaign dung an toan voi exit code $LASTEXITCODE. Chay lai file nay sau khi xem loi; cac seed da xong se duoc bo qua."
}

Write-Host 'Da train xong 6 mo hinh x 3 seed. External test van chua duoc doc/danh gia.' -ForegroundColor Green
