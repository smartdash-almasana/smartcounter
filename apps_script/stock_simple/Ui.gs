function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('StockSimple')
    .addItem('Cargar archivo de stock', 'showCsvImportDialog_')
    .addItem('Ver estado del stock', 'runStockSimple')
    .addItem('Último resultado', 'showLastResult_')
    .addToUi();
}

function configureStockSimple_() {
  var ui = SpreadsheetApp.getUi();
  var current = getConfig_();

  var tenantResp = ui.prompt(
    'Configurar StockSimple',
    'TENANT_ID actual: ' + current.TENANT_ID + '\nIngresar nuevo TENANT_ID:',
    ui.ButtonSet.OK_CANCEL
  );
  if (tenantResp.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var baseUrlResp = ui.prompt(
    'Configurar StockSimple',
    'SMARTCOUNTER_BASE_URL actual: ' + current.SMARTCOUNTER_BASE_URL + '\nIngresar nuevo SMARTCOUNTER_BASE_URL:',
    ui.ButtonSet.OK_CANCEL
  );
  if (baseUrlResp.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var sheetResp = ui.prompt(
    'Configurar StockSimple',
    'SOURCE_SHEET_NAME actual: ' + current.SOURCE_SHEET_NAME + '\nIngresar nuevo SOURCE_SHEET_NAME:',
    ui.ButtonSet.OK_CANCEL
  );
  if (sheetResp.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var headerResp = ui.prompt(
    'Configurar StockSimple',
    'HEADER_ROW actual: ' + current.HEADER_ROW + '\nIngresar nuevo HEADER_ROW (>=1):',
    ui.ButtonSet.OK_CANCEL
  );
  if (headerResp.getSelectedButton() !== ui.Button.OK) {
    return;
  }

  var headerRow = parseInt(headerResp.getResponseText(), 10);
  var nextConfig = {
    TENANT_ID: tenantResp.getResponseText() || current.TENANT_ID,
    SMARTCOUNTER_BASE_URL: baseUrlResp.getResponseText() || current.SMARTCOUNTER_BASE_URL,
    SOURCE_SHEET_NAME: sheetResp.getResponseText() || current.SOURCE_SHEET_NAME,
    HEADER_ROW: isNaN(headerRow) || headerRow < 1 ? current.HEADER_ROW : headerRow
  };

  saveConfig_(nextConfig);
  ui.alert('Configuracion guardada.');
}

function runStockSimple() {
  return runStockSimpleInternal_({ silent: false });
}

function showLastResult_() {
  var props = PropertiesService.getDocumentProperties();
  var raw = props.getProperty('LAST_STOCK_RESULT');
  var ui = SpreadsheetApp.getUi();

  if (!raw) {
    ui.alert('Todavía no hay resultados guardados.');
    return;
  }

  try {
    var result = JSON.parse(raw);
    var message = [
      'Productos analizados: ' + result.total_rows,
      'Alertas detectadas: ' + result.alerts_count,
      'Filas para revisar: ' + result.invalid_rows,
      'Codigo de envio: ' + result.send_code,
      'Deduplicado: ' + (result.deduplicated ? 'Si' : 'No'),
      'Actualizado: ' + result.generated_at
    ].join('\n');
    ui.alert('Último resultado', message, ui.ButtonSet.OK);
  } catch (err) {
    ui.alert('No se pudo leer el Último resultado guardado.');
  }
}

function runStockSimpleInternal_(options) {
  var settings = options || {};
  var silent = !!settings.silent;
  var ui = SpreadsheetApp.getUi();
  var config = getConfig_();

  try {
    var canonicalRows = buildCanonicalRows_();
    var findings = buildFindings_(canonicalRows);
    var summary = buildSummary_(canonicalRows, findings, config.SOURCE_SHEET_NAME);
    var suggestedActions = buildSuggestedActions_(summary, canonicalRows, findings);

    writeCanonicalSheet_(canonicalRows);
    writeFindingsSheet_(findings);
    writeSummarySheet_(summary, suggestedActions);

    var payload = {
      contract_version: 'module-ingestions.v2',
      source_channel: 'apps_script',
      tenant_id: config.TENANT_ID,
      module: 'stock_simple',
      source_type: 'google_sheets',
      generated_at: new Date().toISOString(),
      canonical_rows: canonicalRows,
      findings: findings,
      summary: summary,
      suggested_actions: suggestedActions
    };

    var backendResponse = sendToSmartCounter_(payload);
    var deduplicated = !!(backendResponse.deduplicated || backendResponse.deduped);

    var result = {
      ok: true,
      send_code: backendResponse.ingestion_id,
      deduplicated: deduplicated,
      alerts_count: findings.length,
      total_rows: summary.total_rows,
      valid_rows: summary.valid_rows,
      invalid_rows: summary.invalid_rows,
      generated_at: new Date().toLocaleString()
    };

    PropertiesService.getDocumentProperties().setProperty('LAST_STOCK_RESULT', JSON.stringify(result));

    if (!silent) {
      if (deduplicated) {
        SpreadsheetApp.getActiveSpreadsheet().toast('Ingesta deduplicada. Se reutilizo una ingesta previa.', 'StockSimple', 6);
        ui.alert('Estado del stock actualizado', 'La ingesta fue deduplicada. Codigo de envio: ' + backendResponse.ingestion_id, ui.ButtonSet.OK);
      } else {
        SpreadsheetApp.getActiveSpreadsheet().toast('Listo. Tu estado de stock ya fue actualizado.', 'StockSimple', 6);
        ui.alert('Estado del stock actualizado', 'Se analizaron ' + summary.total_rows + ' productos y se detectaron ' + findings.length + ' alertas.', ui.ButtonSet.OK);
      }
    }

    return result;
  } catch (err) {
    if (!silent) {
      ui.alert('No se pudo actualizar el estado del stock. Revisa el archivo y volve a intentar.');
    }
    throw err;
  }
}
