---
trigger: always_on
---
# ERPNext Playwright Interaction Rules

## Context

ERPNext v16 runs on Frappe Framework v16.1.1. The UI is a single-page application with dynamic DOM rendering. Standard Playwright selectors often fail because Frappe renders fields asynchronously after route change. These rules enforce wait strategies and interaction patterns that are reliable against Frappe's rendering lifecycle.

## Rules

### Page Load — Wait Strategy

- ALWAYS wait for `.page-container` visibility after every `page.goto()` call before any further action
- ALWAYS wait for `networkidle` state to settle after navigation: `waitForLoadState('networkidle')`
- NEVER interact with form fields immediately after navigation — minimum wait: `.form-page` visible
- If `.page-container` does not appear within 10 seconds: classify as "Page load timeout" and STOP

### Login Sequence

- Navigate to `${ERPNEXT_BASE_URL}/login`
- Wait for `#login_email` to be visible
- Fill `#login_email` with value of `ERPNEXT_USERNAME` environment variable
- Fill `#login_password` with value of `ERPNEXT_PASSWORD` environment variable
- Click `[data-label="Login"]` or the primary submit button
- Wait for URL to contain `/app` — timeout 10 seconds
- If URL still contains `/login` after timeout: STOP — do not retry login more than once

### Frappe Field Types — Interaction Rules

#### Text / Data fields
- Use `page.fill('[data-fieldname="{fieldname}"]', value)` where `fieldname` = snake_case field name
- Fallback: locate by label text using `getByLabel('{Field Label}')` if `data-fieldname` not present

#### Link fields (Autocomplete)
- Type partial value into the field
- Wait for `.awesomplete ul li` to appear — timeout 5 seconds
- Click the matching list item — NEVER press Tab or Enter without confirming dropdown appeared
- If dropdown shows "No results": STOP — the linked record does not exist in the system

#### Select fields (Dropdown)
- Use `page.selectOption('[data-fieldname="{fieldname}"] select', '{value}')` 
- If select element not found, use `page.click()` on the field then click the option in dropdown

#### Date fields
- Format MUST be `YYYY-MM-DD` — Frappe parses this regardless of system locale
- Use `page.fill('[data-fieldname="{fieldname}"] input', 'YYYY-MM-DD')`

#### Check fields (Boolean)
- Use `page.check()` or `page.uncheck()` on `[data-fieldname="{fieldname}"] input[type="checkbox"]`

#### Child table rows
1. Click `[data-fieldname="{table_fieldname}"] .btn-open-row` or "Add Row" button
2. Wait for new row `tr` to appear in `[data-fieldname="{table_fieldname}"] .grid-body`
3. Fill each cell using the row's scoped `data-fieldname` selectors
4. Click outside the row to confirm entry before adding next row

### Save and Submission

- Save: click `.page-actions .btn-primary[data-label="Save"]` or `[data-label="Save"]`
- Wait for `.alert-success` toast OR `.msgprint` dialog — timeout 8 seconds
- If `.msgprint` appears: read message text, dismiss with OK button, then check for success/error
- Submit: click `.page-actions [data-label="Submit"]`, wait for confirmation dialog, click "Yes" in dialog, wait for docstatus badge to show "Submitted"
- Cancel: click `.page-actions [data-label="Cancel"]`, confirm dialog, wait for docstatus badge "Cancelled"
- Amend: click `.page-actions [data-label="Amend"]`, wait for new form URL with `-1` suffix or amended name

### Toasts and Errors

- Success toast: `.alert-success` or `.toast.show` with green styling
- Error toast: `.alert-danger` or `.toast.show` with red styling — extract `.toast-body` text verbatim
- Frappe validation error: `.msgprint` with class `.msgprint-dialog` — read `.modal-body` text verbatim
- IF error toast or validation error appears: STOP immediately, report exact error text, do not retry

### Reports

- URL pattern: `${ERPNEXT_BASE_URL}/app/query-report/{Report-Name-With-Hyphens}`
- Wait for `.page-form` to render before setting filters
- Set filters using `[data-fieldname]` selectors within `.page-form`
- Click `[data-label="Run Report"]` or `.btn-run-report`
- Wait for `.dt-wrapper tbody tr` to have at least 1 row — timeout 15 seconds (reports can be slow)
- Extract data by reading `tr td` text content row by row
- If no rows after timeout: report "Report returned 0 rows" — do not treat as error

### Forbidden Patterns

- NEVER use `page.keyboard.press('Tab')` to navigate between Frappe Link fields — always confirm via dropdown
- NEVER use `page.waitForTimeout()` with fixed milliseconds as primary wait strategy — always wait for element or network state
- NEVER interact with elements inside `.modal-backdrop` without first confirming the modal is fully open (`.modal.show`)
- NEVER assume field value was saved until `.alert-success` is confirmed
- NEVER navigate away from a form with unsaved changes — always Save or explicitly discard first

### Permissions and Access Errors

- HTTP 403 / Frappe "Not permitted" error page: STOP — report "Permission denied for this DocType or document. Human must verify role assignment."
- HTTP 404 / "Not Found": STOP — report exact URL attempted and "Document or route does not exist"
- Blank white page after navigation with no `.page-container`: wait 5 seconds, reload once, if still blank: STOP

## Examples

### ✅ Correct — Link field interaction
```
1. page.fill('[data-fieldname="supplier"] input', 'Acme')
2. wait for '.awesomplete ul li' to appear
3. page.click('.awesomplete ul li:has-text("Acme Corp")')
4. confirm field value shows "Acme Corp" before continuing
```

### ❌ Incorrect — Link field interaction
```
1. page.fill('[data-fieldname="supplier"] input', 'Acme Corp')
2. page.keyboard.press('Tab')   ← NEVER do this for Link fields
```

### ✅ Correct — Save confirmation
```
1. page.click('[data-label="Save"]')
2. wait for '.alert-success' visibility
3. report SUCCESS only after toast confirmed
```

### ❌ Incorrect — Save without confirmation
```
1. page.click('[data-label="Save"]')
2. immediately proceed to next step   ← NEVER assume save succeeded
```
