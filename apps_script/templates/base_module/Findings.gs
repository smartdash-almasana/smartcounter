function buildFindings_(ruleResults, cfg) {
  var findings = [];
  var seen = {};

  for (var i = 0; i < ruleResults.length; i += 1) {
    var rr = ruleResults[i];
    var rowFindings = rr.findings || [];

    for (var j = 0; j < rowFindings.length; j += 1) {
      var f = rowFindings[j];
      var key = [rr.row_id, f.code, f.field || ''].join('|');
      if (seen[key]) continue;
      seen[key] = true;

      findings.push({
        finding_code: f.code,
        severity: normalizeSeverity_(f.severity),
        entity_ref: rr.row_id,
        message: f.message
      });
    }
  }

  findings.sort(function(a, b) {
    var ar = severityRank_(a.severity);
    var br = severityRank_(b.severity);
    if (ar !== br) return br - ar;
    if (a.entity_ref !== b.entity_ref) return String(a.entity_ref).localeCompare(String(b.entity_ref));
    return String(a.finding_code).localeCompare(String(b.finding_code));
  });

  return findings;
}

function normalizeSeverity_(value) {
  var s = String(value || '').toLowerCase().trim();
  if (s === 'critical' || s === 'high' || s === 'medium' || s === 'low') return s;
  return 'medium';
}

function severityRank_(s) {
  if (s === 'critical') return 4;
  if (s === 'high') return 3;
  if (s === 'medium') return 2;
  if (s === 'low') return 1;
  return 0;
}
