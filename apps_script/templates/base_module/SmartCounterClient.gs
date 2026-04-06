function validateContract_(contract) {
  if (!contract.tenant_id) throw new Error('Missing tenant_id');
  if (!contract.module) throw new Error('Missing module');
  if (!Array.isArray(contract.canonical_rows)) throw new Error('Invalid canonical_rows');
  if (!Array.isArray(contract.findings)) throw new Error('Invalid findings');
  if (!Array.isArray(contract.suggested_actions)) throw new Error('Invalid suggested_actions');
}

function postIngestAnalyze_(contract, cfg) {
  var base = String(cfg.smartcounter_base_url || '').replace(/\/+$/, '');
  if (!base) throw new Error('Missing SMARTCOUNTER_BASE_URL');
  var url = base + '/ingest/analyze';

  var options = {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(contract),
    muteHttpExceptions: true
  };

  var res = UrlFetchApp.fetch(url, options);
  var status = res.getResponseCode();
  var text = res.getContentText() || '';

  var body;
  try {
    body = JSON.parse(text);
  } catch (e) {
    body = { raw: text };
  }

  return {
    status: status,
    body: body
  };
}
