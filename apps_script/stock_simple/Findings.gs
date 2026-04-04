function buildFindings_(canonicalRows) {
  var findings = [];

  for (var i = 0; i < canonicalRows.length; i += 1) {
    var row = canonicalRows[i];
    var rowFindings = evaluateRowFindings_(row);

    for (var j = 0; j < rowFindings.length; j += 1) {
      var baseFinding = rowFindings[j];
      findings.push({
        finding_id: 'finding_' + (findings.length + 1),
        code: baseFinding.code,
        severity: baseFinding.severity,
        row_id: row.row_id,
        sku: row.sku,
        producto: row.producto,
        message: baseFinding.message,
        evidence: baseFinding.evidence,
        suggested_action_type: baseFinding.suggested_action_type
      });
    }
  }

  return findings;
}
