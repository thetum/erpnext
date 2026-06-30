---
description: >-
  Run an ERPNext Query Report or standard report, apply filters, and return
  structured data
trigger: /erpnext-report
turbo: true
---
# Workflow: /erpnext-report

# ERPNext Report: Run and Extract Data

arguments = $ARGUMENTS
Expected format: `{report-name} [filter1=value1 filter2=value2 ...]`

Examples:
- `Stock Balance item_code="RM-001" warehouse="Stores - MFU"`
- `Accounts Receivable party_type=Customer from_date=2026-01-01 to_date=2026-03-31`
- `Sales Order Trends based_on=Item period=Monthly fiscal_year=2026`

## Preconditions

- [ ] `ERPNEXT_BASE_URL`, `ERPNEXT_USERNAME`, `ERPNEXT_PASSWORD` are set in environment
- [ ] Report name is provided exactly as it appears in ERPNext
- [ ] Filter field names match ERPNext filter parameter names (snake_case)

## Steps

### Step 1: Establish Session
Invoke `.rulesync/skills/erpnext-context/SKILL.md`. Confirm `Ready: YES`.

### Step 2: Parse Arguments

Extract from `$ARGUMENTS`:
- `report_name` — all tokens before the first `=` sign (may be multi-word, e.g. `Stock Balance`)
- `filters` — all `key=value` pairs

Convert `report_name` to URL slug: lowercase, spaces → hyphens (e.g. `Stock Balance` → `stock-balance`)

### Step 3: Navigate to Report

```
page.goto(`${ERPNEXT_BASE_URL}/app/query-report/{report-slug}`)
```

Wait for `.page-form` to be visible — timeout 10 seconds.
If 404 or "Not Found": STOP — report "Report '{report_name}' not found. Verify exact report name in ERPNext."

### Step 4: Apply Filters

For each `filter=value` pair:
1. Locate filter field by `data-fieldname="{filter}"` within `.page-form`
2. Apply value using the field type rules defined in `.rulesync/rules/erpnext-playwright.md` § "Frappe Field Types"
3. For Date filters: format `YYYY-MM-DD`
4. If filter field not found: STOP — report "Filter '{filter}' not found in report '{report_name}'."

If no filters provided: proceed with report defaults.

### Step 5: Run Report

1. Click `[data-label="Run Report"]` or `.btn-run-report` or `[data-label="Refresh"]`
2. Wait for `.dt-wrapper tbody tr` OR `.report-wrapper tbody tr` to contain at least 1 row — timeout 15 seconds
3. If loading spinner persists beyond 15 seconds: STOP — report "Report timed out after 15 seconds."
4. If no rows returned after spinner clears: this is valid — report "Report returned 0 rows with applied filters."

### Step 6: Extract Data

1. Read column headers from `.dt-wrapper thead th` or `.grid-heading-row .col-header` — record column names in order
2. Read maximum 100 rows from `.dt-wrapper tbody tr` — for each row read each `td` text content
3. Map each row to `{column_name: cell_value}` object
4. If report has summary row (`.report-summary`): extract and include separately
5. Note total row count from report footer if visible (`.page-length-select` or `.result-list label`)

## Output Format

```
Action: Run Report
Report: [report name]
Filters Applied:
  {filter1}: {value1}
  {filter2}: {value2}
Result: [SUCCESS | FAILED | STOPPED | EMPTY]
Total Rows: [count or "unknown"]
Rows Returned: [count extracted, max 100]

Data:
| {col1} | {col2} | {col3} | ...
|--------|--------|--------|
| {val}  | {val}  | {val}  | ...
[repeat for each row]

Summary: [summary row values, or "none"]
Error: [exact error text, or "none"]
```

## Stop Conditions

- Session not established
- Report not found (404)
- Filter field not found in report
- Report loading spinner exceeds 15 seconds
- Permission denied error on report page

// turbo
