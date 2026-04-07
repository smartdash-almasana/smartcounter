$baseUrl = "http://127.0.0.1:8010"

Write-Host "🚀 Testing SmartCounter pipeline..." -ForegroundColor Cyan

# 1. POST ingestion
Write-Host "`n📤 Sending ingestion..." -ForegroundColor Yellow

$body = @{
    tenant_id = "debug"
    module = "stock_simple"
    source_type = "google_sheets"
    generated_at = "2026-04-07T12:00:00Z"
    canonical_rows = @()
    findings = @(
        @{
            code = "low_stock_detected"
            severity = "high"
            message = "Producto bajo mínimo"
            suggested_action_type = "generar_documento"
        }
    )
    summary = @{
        total_rows = 0
        valid_rows = 0
        invalid_rows = 0
    }
    suggested_actions = @()
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/module-ingestions" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body

    Write-Host "✅ Ingestion OK" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10
}
catch {
    Write-Host "❌ Ingestion FAILED" -ForegroundColor Red
    Write-Host $_
    exit
}

# 2. Esperar procesamiento
Start-Sleep -Seconds 2

# 3. GET actions
Write-Host "`n📥 Fetching actions..." -ForegroundColor Yellow

try {
    $actions = Invoke-RestMethod -Uri "$baseUrl/actions/latest?tenant_id=debug"

    Write-Host "✅ Actions response:" -ForegroundColor Green
    $actions | ConvertTo-Json -Depth 10

    if ($actions.actions.Count -gt 0) {
        Write-Host "`n🎯 SUCCESS: Actions generated" -ForegroundColor Green
    }
    else {
        Write-Host "`n⚠️ WARNING: No actions generated" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Actions fetch FAILED" -ForegroundColor Red
    Write-Host $_
}