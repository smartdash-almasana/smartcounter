function parseSource_(cfg) {
  var rows = cfg.source_type === 'csv'
    ? parseCsvSource_(cfg)
    : parseSheetSource_(cfg);

  return { canonical_rows: rows };
}

function parseSheetSource_(cfg) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(cfg.source_sheet_name);
  if (!sheet) throw new Error('Source sheet not found: ' + cfg.source_sheet_name);

  var values = sheet.getDataRange().getValues();
  return rowsFromMatrix_(values, cfg.header_row);
}

function parseCsvSource_(cfg) {
  if (!cfg.csv_file_id) throw new Error('CSV_FILE_ID is required when SOURCE_TYPE=csv');
  var file = DriveApp.getFileById(cfg.csv_file_id);
  var csv = file.getBlob().getDataAsString('UTF-8');
  var matrix = Utilities.parseCsv(csv);
  return rowsFromMatrix_(matrix, cfg.header_row);
}

function buildRowId_(row) {
  var base = [
    String(row.date || '').trim(),
    String(row.description || '').trim().toLowerCase(),
    String(row.amount || '').trim()
  ].join('|');

  var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_1, base);
  return bytes.map(function(b) { return (b & 0xFF).toString(16).padStart(2, '0'); }).join('');
}

function rowsFromMatrix_(matrix, headerRow) {
  if (!matrix || matrix.length < headerRow) return [];

  var headers = matrix[headerRow - 1].map(normalizeHeader_);
  var out = [];

  for (var r = headerRow; r < matrix.length; r += 1) {
    var rowArr = matrix[r];
    var raw = {};
    var hasData = false;

    for (var c = 0; c < headers.length; c += 1) {
      var key = headers[c];
      if (!key) continue;
      raw[key] = normalizeText_(rowArr[c]);
      if (raw[key] !== '') hasData = true;
    }
    if (!hasData) continue;

    var amount = parseNumberSafe_(raw.amount);
    var date = raw.date || '';
    var description = raw.description || '';

    var canonical = {
      row_id: '',
      date: date,
      description: description,
      amount: amount,
      valid: Boolean(date && amount !== null),
      raw: raw
    };
    canonical.row_id = buildRowId_(canonical);
    out.push(canonical);
  }

  return out;
}
