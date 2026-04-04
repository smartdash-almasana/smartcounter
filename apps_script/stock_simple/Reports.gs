function buildSummary_(canonicalRows, findings, sourceSheetName) {
  var summary = {
    total_rows: canonicalRows.length,
    valid_rows: 0,
    invalid_rows: 0,
    critical_count: 0,
    low_count: 0,
    overstock_count: 0,
    missing_supplier_count: 0,
    generated_from_sheet: sourceSheetName,
    top_alerts: []
  };

  for (var i = 0; i < canonicalRows.length; i += 1) {
    if (canonicalRows[i].requires_review) {
      summary.invalid_rows += 1;
    } else {
      summary.valid_rows += 1;
    }
  }

  for (var j = 0; j < findings.length; j += 1) {
    var finding = findings[j];
    if (finding.code === STOCKSIMPLE_FINDING_CODES.CRITICAL) {
      summary.critical_count += 1;
    } else if (finding.code === STOCKSIMPLE_FINDING_CODES.LOW) {
      summary.low_count += 1;
    } else if (finding.code === STOCKSIMPLE_FINDING_CODES.OVERSTOCK) {
      summary.overstock_count += 1;
    } else if (finding.code === STOCKSIMPLE_FINDING_CODES.MISSING_SUPPLIER) {
      summary.missing_supplier_count += 1;
    }
  }

  var priority = [
    STOCKSIMPLE_FINDING_CODES.CRITICAL,
    STOCKSIMPLE_FINDING_CODES.LOW,
    STOCKSIMPLE_FINDING_CODES.MISSING_SUPPLIER,
    STOCKSIMPLE_FINDING_CODES.OVERSTOCK,
    STOCKSIMPLE_FINDING_CODES.INVALID_ROW
  ];

  for (var p = 0; p < priority.length; p += 1) {
    var code = priority[p];
    for (var k = 0; k < findings.length; k += 1) {
      if (summary.top_alerts.length >= 5) {
        break;
      }
      if (findings[k].code === code) {
        summary.top_alerts.push({
          code: findings[k].code,
          severity: findings[k].severity,
          row_id: findings[k].row_id,
          sku: findings[k].sku,
          producto: findings[k].producto,
          message: findings[k].message
        });
      }
    }
    if (summary.top_alerts.length >= 5) {
      break;
    }
  }

  return summary;
}

function buildSuggestedActions_(summary, canonicalRows, findings) {
  var actions = [];

  if (summary.critical_count + summary.low_count > 0) {
    actions.push({
      action_id: 'action_' + Utilities.getUuid(),
      action_type: 'generar_documento',
      title: 'Pedido de reposicion sugerido',
      reason: 'Hay productos en riesgo de ruptura',
      payload: {
        critical_count: summary.critical_count,
        low_count: summary.low_count
      }
    });
  }

  var criticalWithSupplier = {};
  for (var i = 0; i < findings.length; i += 1) {
    var finding = findings[i];
    if (finding.code !== STOCKSIMPLE_FINDING_CODES.CRITICAL) {
      continue;
    }

    for (var j = 0; j < canonicalRows.length; j += 1) {
      var row = canonicalRows[j];
      if (row.row_id === finding.row_id && !isBlankValue_(row.proveedor)) {
        criticalWithSupplier[row.row_id] = {
          row_id: row.row_id,
          proveedor: row.proveedor,
          sku: row.sku,
          producto: row.producto
        };
      }
    }
  }

  var criticalWithSupplierRows = Object.keys(criticalWithSupplier).map(function(key) {
    return criticalWithSupplier[key];
  });

  if (criticalWithSupplierRows.length > 0) {
    actions.push({
      action_id: 'action_' + Utilities.getUuid(),
      action_type: 'enviar_mail',
      title: 'Aviso a proveedores por criticidad',
      reason: 'Hay productos criticos con proveedor informado',
      payload: {
        critical_rows_with_supplier: criticalWithSupplierRows
      }
    });
  }

  if (summary.critical_count > 0) {
    actions.push({
      action_id: 'action_' + Utilities.getUuid(),
      action_type: 'crear_evento',
      title: 'Seguimiento urgente de stock critico',
      reason: 'Existe al menos un producto critico',
      payload: {
        critical_count: summary.critical_count
      }
    });
  }

  return actions;
}

function writeCanonicalSheet_(rows) {
  var sheet = getOrCreateOutputSheet_(STOCKSIMPLE_OUTPUT_SHEETS.canonical);
  sheet.clearContents();

  var headers = [
    'Fila',
    'Codigo',
    'Producto',
    'Stock actual',
    'Stock minimo',
    'Consumo diario',
    'Dias de cobertura',
    'Proveedor',
    'Categoria',
    'Revisar'
  ];

  var data = [headers];
  for (var i = 0; i < rows.length; i += 1) {
    data.push([
      rows[i].row_id,
      rows[i].sku,
      rows[i].producto,
      rows[i].stock_actual,
      rows[i].stock_minimo,
      rows[i].consumo_promedio_diario,
      rows[i].dias_cobertura,
      rows[i].proveedor,
      rows[i].categoria_final,
      rows[i].requires_review ? 'Si' : 'No'
    ]);
  }

  sheet.getRange(1, 1, data.length, headers.length).setValues(data);
}

function writeFindingsSheet_(findings) {
  var sheet = getOrCreateOutputSheet_(STOCKSIMPLE_OUTPUT_SHEETS.findings);
  sheet.clearContents();

  var headers = [
    'Alerta',
    'Nivel',
    'Fila',
    'Codigo',
    'Producto',
    'Mensaje',
    'Detalle'
  ];

  var data = [headers];
  for (var i = 0; i < findings.length; i += 1) {
    data.push([
      findings[i].code,
      findings[i].severity,
      findings[i].row_id,
      findings[i].sku,
      findings[i].producto,
      findings[i].message,
      JSON.stringify(findings[i].evidence || {})
    ]);
  }

  sheet.getRange(1, 1, data.length, headers.length).setValues(data);
}

function writeSummarySheet_(summary, suggestedActions) {
  var sheet = getOrCreateOutputSheet_(STOCKSIMPLE_OUTPUT_SHEETS.summary);
  sheet.clearContents();

  var rows = [
    ['Indicador', 'Valor'],
    ['Productos analizados', summary.total_rows],
    ['Filas validas', summary.valid_rows],
    ['Filas para revisar', summary.invalid_rows],
    ['Alertas criticas', summary.critical_count],
    ['Alertas preventivas', summary.low_count],
    ['Posible sobrestock', summary.overstock_count],
    ['Sin proveedor', summary.missing_supplier_count],
    ['Hoja analizada', summary.generated_from_sheet],
    ['Alertas destacadas', JSON.stringify(summary.top_alerts || [])],
    ['Acciones sugeridas', JSON.stringify(suggestedActions || [])]
  ];

  sheet.getRange(1, 1, rows.length, 2).setValues(rows);
}

function getOrCreateOutputSheet_(name) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
  }
  return sheet;
}
