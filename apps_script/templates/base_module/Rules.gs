function evaluateRules_(canonicalRows, cfg) {
  var result = [];

  for (var i = 0; i < canonicalRows.length; i += 1) {
    var row = canonicalRows[i];
    var rowFindings = [];

    for (var j = 0; j < BASE_REQUIRED_FIELDS.length; j += 1) {
      var field = BASE_REQUIRED_FIELDS[j];
      if (!normalizeText_(row[field])) {
        rowFindings.push({
          code: 'missing_required_field',
          severity: 'high',
          field: field,
          message: 'Missing required field: ' + field
        });
      }
    }

    if (row.amount === null) {
      rowFindings.push({
        code: 'invalid_numeric_value',
        severity: 'medium',
        field: 'amount',
        message: 'Invalid numeric value in amount'
      });
    }

    result.push({
      row_id: row.row_id,
      row: row,
      findings: rowFindings
    });
  }

  return { rule_results: result };
}
