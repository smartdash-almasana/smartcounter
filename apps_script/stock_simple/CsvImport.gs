function showCsvImportDialog_() {
  var html = HtmlService.createHtmlOutputFromFile('CsvImportDialog')
    .setWidth(860)
    .setHeight(620);
  SpreadsheetApp.getUi().showModalDialog(html, 'Cargar archivo de stock');
}

function previewCsvImport_(csvText, filename) {
  if (!csvText || !String(csvText).trim()) {
    throw new Error('El archivo esta vacio.');
  }

  var delimiter = detectDelimiter_(csvText);
  var rows = parseCsvRows_(csvText, delimiter);
  if (!rows.length) {
    throw new Error('No se encontraron datos en el archivo.');
  }

  var headers = rows[0];
  var validation = validateCsvHeaders_(headers);

  var previewRows = [];
  for (var i = 1; i < rows.length && previewRows.length < 5; i += 1) {
    previewRows.push(rows[i]);
  }

  return {
    filename: filename || '',
    delimiter: delimiter,
    total_rows: rows.length - 1,
    headers: headers,
    recognized_headers: validation.recognizedHeaders,
    missing_required_headers: validation.missing,
    valid: validation.missing.length === 0,
    preview_rows: previewRows
  };
}

function importCsvToStockSheet_(csvText, filename) {
  if (!csvText || !String(csvText).trim()) {
    throw new Error('El archivo esta vacio.');
  }

  var delimiter = detectDelimiter_(csvText);
  var rows = parseCsvRows_(csvText, delimiter);
  if (!rows.length) {
    throw new Error('No se encontraron datos en el archivo.');
  }

  var validation = validateCsvHeaders_(rows[0]);
  if (validation.missing.length > 0) {
    throw new Error('No se puede continuar. Faltan datos clave: ' + validation.missing.join(', '));
  }

  var importedCount = replaceSourceSheetWithCsv_(rows);
  var analysis = runStockSimpleInternal_({ silent: true });

  return {
    ok: true,
    filename: filename || '',
    imported_rows: importedCount,
    alerts_count: analysis.alerts_count,
    send_code: analysis.send_code,
    total_rows: analysis.total_rows,
    valid_rows: analysis.valid_rows,
    invalid_rows: analysis.invalid_rows
  };
}

function detectDelimiter_(csvText) {
  var lines = String(csvText || '').split(/\r?\n/);
  var bestLine = '';

  for (var i = 0; i < lines.length && i < 20; i += 1) {
    var trimmed = String(lines[i] || '').trim();
    if (!trimmed) {
      continue;
    }
    if (trimmed.length > bestLine.length) {
      bestLine = trimmed;
    }
  }

  if (!bestLine) {
    return ',';
  }

  var commaCount = (bestLine.match(/,/g) || []).length;
  var semicolonCount = (bestLine.match(/;/g) || []).length;

  if (semicolonCount > commaCount) {
    return ';';
  }
  return ',';
}

function parseCsvRows_(csvText, delimiter) {
  var rawRows = Utilities.parseCsv(csvText, delimiter || ',');
  var normalizedRows = [];

  for (var i = 0; i < rawRows.length; i += 1) {
    var row = rawRows[i];
    var cleanedRow = [];
    var hasContent = false;

    for (var j = 0; j < row.length; j += 1) {
      var cell = normalizeString_(row[j]);
      cleanedRow.push(cell);
      if (cell !== '') {
        hasContent = true;
      }
    }

    if (hasContent) {
      normalizedRows.push(cleanedRow);
    }
  }

  if (!normalizedRows.length) {
    return [];
  }

  var maxCols = 0;
  for (var k = 0; k < normalizedRows.length; k += 1) {
    if (normalizedRows[k].length > maxCols) {
      maxCols = normalizedRows[k].length;
    }
  }

  for (var x = 0; x < normalizedRows.length; x += 1) {
    while (normalizedRows[x].length < maxCols) {
      normalizedRows[x].push('');
    }
  }

  return normalizedRows;
}

function replaceSourceSheetWithCsv_(rows) {
  var config = getConfig_();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(config.SOURCE_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(config.SOURCE_SHEET_NAME);
  }

  sheet.clearContents();

  var rowWidth = rows[0].length;
  var valuesToWrite = [];

  for (var i = 1; i < config.HEADER_ROW; i += 1) {
    valuesToWrite.push(createBlankRow_(rowWidth));
  }

  for (var j = 0; j < rows.length; j += 1) {
    valuesToWrite.push(rows[j]);
  }

  if (!valuesToWrite.length) {
    throw new Error('No hay datos para cargar.');
  }

  sheet.getRange(1, 1, valuesToWrite.length, rowWidth).setValues(valuesToWrite);
  return rows.length - 1;
}

function validateCsvHeaders_(headers) {
  var headerIndexMap = buildHeaderIndexMap_(headers || []);
  var missing = [];
  var recognizedHeaders = {};

  for (var i = 0; i < STOCKSIMPLE_REQUIRED_HEADERS.length; i += 1) {
    var field = STOCKSIMPLE_REQUIRED_HEADERS[i];
    if (headerIndexMap[field] === undefined) {
      missing.push(field);
    } else {
      recognizedHeaders[field] = normalizeString_(headers[headerIndexMap[field]]);
    }
  }

  return {
    missing: missing,
    recognizedHeaders: recognizedHeaders
  };
}

function createBlankRow_(size) {
  var row = [];
  for (var i = 0; i < size; i += 1) {
    row.push('');
  }
  return row;
}
