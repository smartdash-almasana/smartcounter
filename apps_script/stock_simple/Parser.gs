function buildCanonicalRows_() {
  var config = getConfig_();
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sourceSheet = ss.getSheetByName(config.SOURCE_SHEET_NAME);

  if (!sourceSheet) {
    throw new Error('No se encontro la hoja fuente: ' + config.SOURCE_SHEET_NAME);
  }

  var allValues = sourceSheet.getDataRange().getValues();
  if (allValues.length < config.HEADER_ROW) {
    throw new Error('HEADER_ROW fuera de rango para la hoja fuente.');
  }

  var headerValues = allValues[config.HEADER_ROW - 1];
  var headerIndexMap = buildHeaderIndexMap_(headerValues);

  var missing = [];
  for (var i = 0; i < STOCKSIMPLE_REQUIRED_HEADERS.length; i += 1) {
    var field = STOCKSIMPLE_REQUIRED_HEADERS[i];
    if (headerIndexMap[field] === undefined) {
      missing.push(field);
    }
  }

  if (missing.length > 0) {
    throw new Error('Faltan columnas requeridas: ' + missing.join(', '));
  }

  var rows = [];
  var firstDataRow = config.HEADER_ROW + 1;

  for (var rowNumber = firstDataRow; rowNumber <= allValues.length; rowNumber += 1) {
    var rawRow = allValues[rowNumber - 1];

    var rawSku = rawRow[headerIndexMap.sku];
    var rawProducto = rawRow[headerIndexMap.producto];
    var rawStockActual = rawRow[headerIndexMap.stock_actual];
    var rawStockMinimo = rawRow[headerIndexMap.stock_minimo];
    var rawConsumoDiario = rawRow[headerIndexMap.consumo_promedio_diario];
    var rawProveedor = rawRow[headerIndexMap.proveedor];

    var rowIsEmpty = isBlankValue_(rawSku)
      && isBlankValue_(rawProducto)
      && isBlankValue_(rawStockActual)
      && isBlankValue_(rawStockMinimo)
      && isBlankValue_(rawConsumoDiario)
      && isBlankValue_(rawProveedor);

    if (rowIsEmpty) {
      continue;
    }

    var sku = normalizeString_(rawSku);
    var producto = normalizeString_(rawProducto);
    var proveedor = normalizeString_(rawProveedor);

    var stockActualParsed = parseNumber_(rawStockActual);
    var stockMinimoParsed = parseNumber_(rawStockMinimo);
    var consumoParsed = parseNumber_(rawConsumoDiario);

    var valid = true;

    if (!producto) {
      valid = false;
    }
    if (!stockActualParsed.isNumeric) {
      valid = false;
    }
    if (!stockMinimoParsed.isNumeric) {
      valid = false;
    }
    if (!consumoParsed.isNumeric) {
      valid = false;
    }

    if (stockActualParsed.isNumeric && stockActualParsed.value < 0) {
      valid = false;
    }
    if (stockMinimoParsed.isNumeric && stockMinimoParsed.value < 0) {
      valid = false;
    }
    if (consumoParsed.isNumeric && consumoParsed.value < 0) {
      valid = false;
    }

    var stockActual = stockActualParsed.isNumeric ? stockActualParsed.value : 0;
    var stockMinimo = stockMinimoParsed.isNumeric ? stockMinimoParsed.value : 0;
    var consumoDiario = consumoParsed.isNumeric ? consumoParsed.value : 0;

    var diasCobertura = 0;
    if (valid) {
      if (consumoDiario > 0) {
        diasCobertura = stockActual / consumoDiario;
      } else {
        diasCobertura = 999999;
      }
    }

    rows.push({
      row_id: 'stock_row_' + rowNumber,
      sku: sku || null,
      producto: producto,
      stock_actual: Number(stockActual),
      stock_minimo: Number(stockMinimo),
      consumo_promedio_diario: Number(consumoDiario),
      dias_cobertura: Number(diasCobertura),
      proveedor: proveedor || null,
      categoria_final: 'stock_item',
      requires_review: !valid
    });
  }

  return rows;
}
