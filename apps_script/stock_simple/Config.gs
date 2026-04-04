var STOCKSIMPLE_OUTPUT_SHEETS = {
  canonical: 'Stock_Ordenado',
  findings: 'Alertas_Stock',
  summary: 'Resumen_Stock'
};

var STOCKSIMPLE_REQUIRED_HEADERS = [
  'sku',
  'producto',
  'stock_actual',
  'stock_minimo',
  'consumo_promedio_diario',
  'proveedor'
];

var STOCKSIMPLE_HEADER_ALIASES = {
  sku: ['sku', 'codigo', 'codigo_sku', 'cod_sku'],
  producto: ['producto', 'nombre_producto', 'articulo', 'item'],
  stock_actual: ['stock_actual', 'stock', 'existencia_actual', 'cantidad_actual'],
  stock_minimo: ['stock_minimo', 'minimo', 'stock_min', 'punto_reposicion'],
  consumo_promedio_diario: ['consumo_promedio_diario', 'consumo_diario', 'promedio_diario', 'venta_diaria_promedio'],
  proveedor: ['proveedor', 'supplier', 'vendor']
};

var STOCKSIMPLE_FINDING_CODES = {
  LOW: 'low_stock_detected',
  CRITICAL: 'critical_stock_detected',
  OVERSTOCK: 'overstock_detected',
  MISSING_SUPPLIER: 'missing_supplier',
  INVALID_ROW: 'invalid_stock_row'
};

var STOCKSIMPLE_SEVERITIES = {
  low_stock_detected: 'medium',
  critical_stock_detected: 'high',
  overstock_detected: 'low',
  missing_supplier: 'medium',
  invalid_stock_row: 'medium'
};

function getConfig_() {
  var props = PropertiesService.getDocumentProperties();
  var headerRaw = props.getProperty('HEADER_ROW');
  var headerRow = parseInt(headerRaw, 10);

  return {
    TENANT_ID: (props.getProperty('TENANT_ID') || 'demo001').trim(),
    SMARTCOUNTER_BASE_URL: (props.getProperty('SMARTCOUNTER_BASE_URL') || 'https://TU_BACKEND_PUBLICO').trim(),
    SOURCE_SHEET_NAME: (props.getProperty('SOURCE_SHEET_NAME') || 'Stock').trim(),
    HEADER_ROW: isNaN(headerRow) || headerRow < 1 ? 1 : headerRow
  };
}

function saveConfig_(config) {
  var props = PropertiesService.getDocumentProperties();
  props.setProperty('TENANT_ID', String(config.TENANT_ID || '').trim());
  props.setProperty('SMARTCOUNTER_BASE_URL', String(config.SMARTCOUNTER_BASE_URL || '').trim());
  props.setProperty('SOURCE_SHEET_NAME', String(config.SOURCE_SHEET_NAME || '').trim());
  props.setProperty('HEADER_ROW', String(config.HEADER_ROW || 1));
}

function normalizeHeader_(value) {
  return String(value || '')
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, '_');
}

function normalizeString_(value) {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value).trim();
}

function parseNumber_(value) {
  if (value === null || value === undefined || String(value).trim() === '') {
    return { isNumeric: false, value: null };
  }

  if (typeof value === 'number') {
    return { isNumeric: !isNaN(value), value: Number(value) };
  }

  var raw = String(value)
    .replace(/\u00A0/g, ' ')
    .trim();

  if (!raw) {
    return { isNumeric: false, value: null };
  }

  var isParenNegative = /^\(.*\)$/.test(raw);
  if (isParenNegative) {
    raw = raw.substring(1, raw.length - 1);
  }

  var cleaned = raw
    .replace(/\s+/g, '')
    .replace(/[^0-9,\.\-]/g, '');

  if (!cleaned || !/[0-9]/.test(cleaned)) {
    return { isNumeric: false, value: null };
  }

  var minusCount = (cleaned.match(/-/g) || []).length;
  if (minusCount > 1 || (minusCount === 1 && cleaned.indexOf('-') !== 0)) {
    return { isNumeric: false, value: null };
  }

  var isNegative = isParenNegative || cleaned.indexOf('-') === 0;
  if (cleaned.indexOf('-') === 0) {
    cleaned = cleaned.substring(1);
  }

  if (!cleaned || !/[0-9]/.test(cleaned)) {
    return { isNumeric: false, value: null };
  }

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

  if (!normalized || normalized === '.' || !/^\d+(\.\d+)?$/.test(normalized)) {
    return { isNumeric: false, value: null };
  }

  var parsed = Number(normalized);
  if (isNaN(parsed)) {
    return { isNumeric: false, value: null };
  }

  if (isNegative) {
    parsed = -parsed;
  }

  return { isNumeric: true, value: parsed };
}

function inferDecimalSeparator_(numericString, sep) {
  var count = (numericString.match(new RegExp('\\' + sep, 'g')) || []).length;
  if (count === 0) {
    return null;
  }

  var parts = numericString.split(sep);
  if (count === 1) {
    var digitsAfter = parts[1].length;
    if (digitsAfter === 3 && parts[0].length >= 1) {
      return null;
    }
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

function isBlankValue_(value) {
  return value === null || value === undefined || String(value).trim() === '';
}

function buildHeaderIndexMap_(headers) {
  var normalizedToIndex = {};
  for (var i = 0; i < headers.length; i += 1) {
    var key = normalizeHeader_(headers[i]);
    if (key && normalizedToIndex[key] === undefined) {
      normalizedToIndex[key] = i;
    }
  }

  var headerIndexMap = {};
  for (var field in STOCKSIMPLE_HEADER_ALIASES) {
    if (!Object.prototype.hasOwnProperty.call(STOCKSIMPLE_HEADER_ALIASES, field)) {
      continue;
    }

    var aliases = STOCKSIMPLE_HEADER_ALIASES[field];
    for (var j = 0; j < aliases.length; j += 1) {
      var aliasKey = normalizeHeader_(aliases[j]);
      if (normalizedToIndex[aliasKey] !== undefined) {
        headerIndexMap[field] = normalizedToIndex[aliasKey];
        break;
      }
    }
  }

  return headerIndexMap;
}
