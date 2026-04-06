function buildSummary_(canonicalRows, findings, cfg) {
  var totalRows = canonicalRows.length;
  var findingsCount = findings.length;

  var high = 0;
  var medium = 0;
  var low = 0;
  var affected = {};

  for (var i = 0; i < findings.length; i += 1) {
    var f = findings[i];
    affected[f.entity_ref] = true;
    if (f.severity === 'critical' || f.severity === 'high') high += 1;
    else if (f.severity === 'medium') medium += 1;
    else low += 1;
  }

  var invalidRows = Object.keys(affected).length;
  var validRows = Math.max(0, totalRows - invalidRows);

  return {
    total_rows: totalRows,
    valid_rows: validRows,
    invalid_rows: invalidRows,
    findings_count: findingsCount,
    high_severity: high,
    medium_severity: medium,
    low_severity: low
  };
}

function buildSuggestedActions_(findings, cfg) {
  var hasMissing = false;
  var hasInvalidNumeric = false;

  for (var i = 0; i < findings.length; i += 1) {
    var code = findings[i].finding_code;
    if (code === 'missing_required_field') hasMissing = true;
    if (code === 'invalid_numeric_value') hasInvalidNumeric = true;
  }

  var actions = [];
  actions.push({
    action_type: 'review_data',
    title: 'Review records with findings',
    priority: 'medium'
  });

  if (hasMissing) {
    actions.push({
      action_type: 'fix_missing_fields',
      title: 'Complete required fields',
      priority: 'high'
    });
  }

  if (hasInvalidNumeric) {
    actions.push({
      action_type: 'normalize_numeric_format',
      title: 'Normalize numeric formats',
      priority: 'medium'
    });
  }

  actions.sort(function(a, b) {
    var rank = { high: 3, medium: 2, low: 1 };
    var ar = rank[a.priority] || 0;
    var br = rank[b.priority] || 0;
    if (ar !== br) return br - ar;
    return a.action_type.localeCompare(b.action_type);
  });

  return actions.slice(0, 3);
}

function writeOutputSheet_(contract) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(BASE_OUTPUT_SHEET) || ss.insertSheet(BASE_OUTPUT_SHEET);
  sheet.clear();

  var rows = [
    ['tenant_id', contract.tenant_id],
    ['module', contract.module],
    ['source_type', contract.source_type],
    ['generated_at', contract.generated_at],
    ['canonical_rows', contract.canonical_rows.length],
    ['findings', contract.findings.length],
    ['suggested_actions', contract.suggested_actions.length]
  ];

  sheet.getRange(1, 1, rows.length, 2).setValues(rows);
}
