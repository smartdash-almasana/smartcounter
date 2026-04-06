var BASE_OUTPUT_SHEET = 'SmartCounter_Output';
var BASE_REQUIRED_FIELDS = ['date', 'description', 'amount'];

function getConfig_() {
  var props = PropertiesService.getDocumentProperties();
  var headerRaw = props.getProperty('HEADER_ROW');
  var headerRow = parseInt(headerRaw, 10);

  return {
    tenant_id: (props.getProperty('TENANT_ID') || 'demo001').trim(),
    module: (props.getProperty('MODULE_NAME') || 'base_module').trim(),
    source_type: (props.getProperty('SOURCE_TYPE') || 'google_sheets').trim(),
    source_sheet_name: (props.getProperty('SOURCE_SHEET_NAME') || 'Data').trim(),
    csv_file_id: (props.getProperty('CSV_FILE_ID') || '').trim(),
    header_row: isNaN(headerRow) || headerRow < 1 ? 1 : headerRow,
    smartcounter_base_url: (props.getProperty('SMARTCOUNTER_BASE_URL') || 'https://YOUR_BACKEND').trim()
  };
}

function saveConfig_(config) {
  var props = PropertiesService.getDocumentProperties();
  props.setProperty('TENANT_ID', String(config.tenant_id || '').trim());
  props.setProperty('MODULE_NAME', String(config.module || 'base_module').trim());
  props.setProperty('SOURCE_TYPE', String(config.source_type || 'google_sheets').trim());
  props.setProperty('SOURCE_SHEET_NAME', String(config.source_sheet_name || 'Data').trim());
  props.setProperty('CSV_FILE_ID', String(config.csv_file_id || '').trim());
  props.setProperty('HEADER_ROW', String(config.header_row || 1));
  props.setProperty('SMARTCOUNTER_BASE_URL', String(config.smartcounter_base_url || '').trim());
}

function nowIso_() {
  return new Date().toISOString();
}

function normalizeHeader_(value) {
  return String(value || '')
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '_');
}

function normalizeText_(value) {
  if (value === null || value === undefined) return '';
  return String(value).trim();
}

function parseNumberSafe_(value) {
  if (value === null || value === undefined || String(value).trim() === '') return null;
  if (typeof value === 'number') return isNaN(value) ? null : Number(value);

  var raw = String(value).replace(/\u00A0/g, ' ').trim();
  var isParenNegative = /^\(.*\)$/.test(raw);
  if (isParenNegative) raw = raw.substring(1, raw.length - 1);

  var cleaned = raw.replace(/\s+/g, '').replace(/[^0-9,\.\-]/g, '');
  if (!cleaned || !/[0-9]/.test(cleaned)) return null;

  var minusCount = (cleaned.match(/-/g) || []).length;
  if (minusCount > 1 || (minusCount === 1 && cleaned.indexOf('-') !== 0)) return null;

  var isNegative = isParenNegative || cleaned.indexOf('-') === 0;
  if (cleaned.indexOf('-') === 0) cleaned = cleaned.substring(1);

  var commaCount = (cleaned.match(/,/g) || []).length;
  var dotCount = (cleaned.match(/\./g) || []).length;
  var decimalSep = null;

  if (commaCount > 0 && dotCount > 0) {
    decimalSep = cleaned.lastIndexOf(',') > cleaned.lastIndexOf('.') ? ',' : '.';
  } else if (commaCount > 0) {
    decimalSep = inferDecimalSeparator_(cleaned, ',');
  } else if (dotCount > 0) {
    decimalSep = inferDecimalSeparator_(cleaned, '.');
  }

  var normalized;
  if (decimalSep) {
    var lastIdx = cleaned.lastIndexOf(decimalSep);
    var intPart = cleaned.substring(0, lastIdx).replace(/[\.,]/g, '');
    var fracPart = cleaned.substring(lastIdx + 1).replace(/[\.,]/g, '');
    normalized = intPart + '.' + fracPart;
  } else {
    normalized = cleaned.replace(/[\.,]/g, '');
  }

  if (!normalized || normalized === '.' || !/^\d+(\.\d+)?$/.test(normalized)) return null;
  var parsed = Number(normalized);
  if (isNaN(parsed)) return null;
  return isNegative ? -parsed : parsed;
}

function inferDecimalSeparator_(numericString, sep) {
  var count = (numericString.match(new RegExp('\\' + sep, 'g')) || []).length;
  if (count === 0) return null;

  var parts = numericString.split(sep);
  if (count === 1) {
    var digitsAfter = parts[1].length;
    if (digitsAfter === 3 && parts[0].length >= 1) return null;
    return digitsAfter > 0 ? sep : null;
  }

  var allThree = true;
  for (var i = 1; i < parts.length; i += 1) {
    if (parts[i].length !== 3) {
      allThree = false;
      break;
    }
  }
  return allThree ? null : sep;
}
