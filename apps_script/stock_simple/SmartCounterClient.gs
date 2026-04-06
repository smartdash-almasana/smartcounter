function sendToSmartCounter_(payload) {
  var config = getConfig_();
  var baseUrl = (config.SMARTCOUNTER_BASE_URL || '').replace(/\/$/, '');
  if (!baseUrl) {
    throw new Error('SMARTCOUNTER_BASE_URL no configurado.');
  }

  var endpoint = baseUrl + '/module-ingestions';

  var response = UrlFetchApp.fetch(endpoint, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });

  var code = response.getResponseCode();
  var body = response.getContentText();

  if (code < 200 || code >= 300) {
    throw new Error('SmartCounter respondio ' + code + ': ' + body);
  }

  var parsed;
  try {
    parsed = JSON.parse(body);
  } catch (err) {
    throw new Error('Respuesta no JSON desde SmartCounter: ' + body);
  }

  if (!parsed.ok || !parsed.ingestion_id) {
    throw new Error('Respuesta invalida desde SmartCounter: ' + body);
  }

  // Compatibilidad: backend puede responder deduplicated o deduped.
  if (parsed.deduplicated === undefined && parsed.deduped !== undefined) {
    parsed.deduplicated = !!parsed.deduped;
  }

  return parsed;
}
