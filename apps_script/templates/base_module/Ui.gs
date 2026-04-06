function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('SmartCounter')
    .addItem('Run Analysis', 'runAnalysis')
    .addToUi();
}

function runAnalysis() {
  var lock = LockService.getDocumentLock();
  lock.waitLock(30000);

  try {
    var cfg = getConfig_();

    var parsed = parseSource_(cfg);
    var rulesResult = evaluateRules_(parsed.canonical_rows, cfg);
    var findings = buildFindings_(rulesResult.rule_results, cfg);
    var summary = buildSummary_(parsed.canonical_rows, findings, cfg);
    var actions = buildSuggestedActions_(findings, cfg);

    var contract = {
      tenant_id: cfg.tenant_id,
      module: cfg.module,
      source_type: cfg.source_type,
      generated_at: nowIso_(),
      canonical_rows: parsed.canonical_rows,
      findings: findings,
      summary: summary,
      suggested_actions: actions
    };

    validateContract_(contract);
    writeOutputSheet_(contract);

    var apiResult = postIngestAnalyze_(contract, cfg);

    SpreadsheetApp.getUi().alert(
      'SmartCounter run completed.\n' +
      'Rows: ' + contract.canonical_rows.length + '\n' +
      'Findings: ' + contract.findings.length + '\n' +
      'HTTP: ' + apiResult.status
    );
  } finally {
    lock.releaseLock();
  }
}
