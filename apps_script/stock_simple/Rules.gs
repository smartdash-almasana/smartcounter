function evaluateRowFindings_(row) {
  var results = [];

  if (row.requires_review) {
    results.push({
      code: STOCKSIMPLE_FINDING_CODES.INVALID_ROW,
      severity: STOCKSIMPLE_SEVERITIES.invalid_stock_row,
      message: 'Fila invalida para analisis de stock. Revisar valores requeridos.',
      evidence: {
        stock_actual: row.stock_actual,
        stock_minimo: row.stock_minimo,
        consumo_promedio_diario: row.consumo_promedio_diario,
        producto: row.producto
      },
      suggested_action_type: 'crear_evento'
    });
    return results;
  }

  var isCritical = row.stock_actual <= 0 || row.dias_cobertura <= 3;

  if (isCritical) {
    results.push({
      code: STOCKSIMPLE_FINDING_CODES.CRITICAL,
      severity: STOCKSIMPLE_SEVERITIES.critical_stock_detected,
      message: 'Stock critico: cobertura <= 3 dias o stock sin unidades.',
      evidence: {
        stock_actual: row.stock_actual,
        dias_cobertura: row.dias_cobertura
      },
      suggested_action_type: 'generar_documento'
    });
  }

  var isLow = !isCritical && (row.stock_actual <= row.stock_minimo || (row.dias_cobertura > 3 && row.dias_cobertura <= 7));
  if (isLow) {
    results.push({
      code: STOCKSIMPLE_FINDING_CODES.LOW,
      severity: STOCKSIMPLE_SEVERITIES.low_stock_detected,
      message: 'Stock bajo: por debajo del minimo o cobertura <= 7 dias.',
      evidence: {
        stock_actual: row.stock_actual,
        stock_minimo: row.stock_minimo,
        dias_cobertura: row.dias_cobertura
      },
      suggested_action_type: 'generar_documento'
    });
  }

  if (row.consumo_promedio_diario > 0 && row.dias_cobertura >= 45) {
    results.push({
      code: STOCKSIMPLE_FINDING_CODES.OVERSTOCK,
      severity: STOCKSIMPLE_SEVERITIES.overstock_detected,
      message: 'Sobrestock detectado: cobertura >= 45 dias.',
      evidence: {
        stock_actual: row.stock_actual,
        dias_cobertura: row.dias_cobertura
      },
      suggested_action_type: 'crear_evento'
    });
  }

  if (isBlankValue_(row.proveedor)) {
    results.push({
      code: STOCKSIMPLE_FINDING_CODES.MISSING_SUPPLIER,
      severity: STOCKSIMPLE_SEVERITIES.missing_supplier,
      message: 'Proveedor faltante para producto con stock gestionable.',
      evidence: {
        proveedor: row.proveedor
      },
      suggested_action_type: 'enviar_mail'
    });
  }

  return results;
}
