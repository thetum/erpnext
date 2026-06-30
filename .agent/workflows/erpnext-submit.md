---
description: >-
  Submit, Cancel, or Amend a single ERPNext document — manages document workflow
  state via Playwright
trigger: /erpnext-submit
turbo: true
---
# Workflow: /erpnext-submit

# ERPNext Document: Submit / Cancel / Amend

arguments = $ARGUMENTS
Expected format: `{action} {doctype} {docname}`

Valid actions: `submit`, `cancel`, `amend`

Examples:
- `submit Purchase Order PO-2026-00042`
- `cancel Sales Invoice ACC-SINV-2026-00017`
- `amend Purchase Invoice ACC-PINV-2026-00009`

## Preconditions

- [ ] `ERPNEXT_BASE_URL`, `ERPNEXT_USERNAME`, `ERPNEXT_PASSWORD` are set in environment
- [ ] `action` is one of: `submit`, `cancel`, `amend`
- [ ] `doctype` is provided
- [ ] `docname` is provided and is the exact ERPNext document name
- [ ] For `submit`: document must be in Draft state (docstatus = 0)
- [ ] For `cancel`: document must be in Submitted state (docstatus = 1) — explicit human authorization required in task message
- [ ] For `amend`: document must be in Cancelled state (docstatus = 2)

## Steps

### Step 1: Establish Session
Invoke `.rulesync/skills/erpnext-context/SKILL.md`. Confirm `Ready: YES`.

### Step 2: Parse and Validate Arguments

Extract `action`, `doctype`, `docname` from `$ARGUMENTS`.

If any are missing: STOP — report "Required: action (submit|cancel|amend), doctype, docname."
If `action` is not one of `submit`, `cancel`, `amend`: STOP — report "Invalid action '{action}'. Use: submit, cancel, amend."

### Step 3: Navigate to Document

```
page.goto(`${ERPNEXT_BASE_URL}/app/{doctype-slug}/{docname}`)
```

Wait for `.form-page` to be visible — timeout 10 seconds.
If 404: STOP — report "Document '{docname}' not found."
If permission error: STOP — report "Permission denied for '{docname}'."

### Step 4: Verify Current Document State

Read docstatus indicator:
- `.page-head .indicator-pill.draft` OR `.indicator-pill:has-text("Draft")` → docstatus = 0 (Draft)
- `.page-head .indicator-pill.orange` OR `.indicator-pill:has-text("Submitted")` → docstatus = 1 (Submitted)
- `.page-head .indicator-pill.red` OR `.indicator-pill:has-text("Cancelled")` → docstatus = 2 (Cancelled)

Validate action against current state:

| Action | Required State | If Wrong State |
|--------|---------------|----------------|
| submit | Draft (0) | STOP — "Document is not in Draft state. Current: {state}" |
| cancel | Submitted (1) | STOP — "Document is not in Submitted state. Current: {state}" |
| amend  | Cancelled (2) | STOP — "Document is not in Cancelled state. Current: {state}" |

### Step 5: Execute Action

#### Submit
1. Click `.page-actions [data-label="Submit"]`
2. Wait for confirmation dialog `.modal.show` — confirm dialog title contains "Submit"
3. Click "Yes" button within dialog: `.modal.show .btn-primary:has-text("Yes")`
4. Wait for docstatus indicator to change to "Submitted" (orange) — timeout 10 seconds
5. If error toast appears: STOP — report exact error text

#### Cancel
1. Verify task message contains explicit cancel authorization — if not: STOP — report "Cancel requires explicit authorization in the current task message. Restate the task with 'cancel {docname}' to confirm."
2. Click `.page-actions [data-label="Cancel"]`
3. Wait for confirmation dialog `.modal.show`
4. Click "Yes" within dialog
5. Wait for docstatus indicator to change to "Cancelled" (red) — timeout 10 seconds
6. If error toast appears: STOP — report exact error text

#### Amend
1. Click `.page-actions [data-label="Amend"]`
2. Wait for new form page to load — URL must change to new document (typically `{docname}-1` suffix or new name)
3. Wait for `.form-page` with docstatus indicator "Draft"
4. Confirm new document name from URL or page title

### Step 6: Confirm Final State

After action completes, read and confirm:
- Final docstatus indicator text
- Document name (may change on Amend)
- Any workflow state field if visible

## Output Format

```
Action: [Submit | Cancel | Amend]
DocType: [doctype]
Document: [docname]
Previous State: [Draft | Submitted | Cancelled]
Final State: [Submitted | Cancelled | Draft (Amended)]
Amended Document Name: [new docname, or "N/A"]
Result: [SUCCESS | FAILED | STOPPED]
Error: [exact error text, or "none"]
Next Step: [human action required, or "none"]
```

## Stop Conditions

- Session not established
- Document not found or permission denied
- Action does not match current document state
- Cancel action attempted without explicit authorization in task message
- Confirmation dialog does not appear within 5 seconds of clicking action button
- Docstatus indicator does not change within 10 seconds after confirming dialog
- Error toast appears at any point during action
- More than one document would be affected — this command operates on exactly one document per invocation

// turbo
