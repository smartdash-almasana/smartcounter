# SmartCounter Apps Script Base Module Template

This is a reusable Google Apps Script template for SmartCounter-compatible modules.

## Files

- `Config.gs`: Configuration and shared helpers
- `Ui.gs`: Spreadsheet menu and execution flow
- `Parser.gs`: Reads Google Sheet/CSV and builds canonical rows
- `Rules.gs`: Deterministic rule evaluation
- `Findings.gs`: Generates findings array
- `Reports.gs`: Builds summary and suggested actions
- `SmartCounterClient.gs`: Contract validation and POST to backend

## SmartCounter Contract

```json
{
  "tenant_id": "string",
  "module": "string",
  "source_type": "google_sheets|csv",
  "generated_at": "ISO-8601",
  "canonical_rows": [],
  "findings": [],
  "summary": {},
  "suggested_actions": []
}
```

## Install

1. Open a Google Spreadsheet.
2. Go to `Extensions > Apps Script`.
3. Create files with the same names as this template.
4. Copy/paste each file content.
5. Save and run `onOpen` once to grant permissions.

## Configure

Set Document Properties:

- `TENANT_ID`
- `MODULE_NAME`
- `SOURCE_TYPE` (`google_sheets` or `csv`)
- `SOURCE_SHEET_NAME` (for sheets)
- `CSV_FILE_ID` (for csv)
- `HEADER_ROW`
- `SMARTCOUNTER_BASE_URL`

## Run

Use menu: `SmartCounter > Run Analysis`.

Flow:

1. parse
2. rules
3. findings
4. summary
5. suggested actions
6. validate contract
7. send to `/ingest/analyze`

## Create a new module

1. Copy `base_module` folder.
2. Update `MODULE_NAME` and business rules.
3. Keep output contract unchanged.
4. Keep deterministic ordering.
