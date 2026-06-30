---
description: >-
  Fill or edit an ERPNext DocType form — create new or open existing document,
  set field values, and save
trigger: /erpnext-form
turbo: true
---
# Workflow: /erpnext-form

# ERPNext Form: Fill / Edit

arguments = $ARGUMENTS
Expected format: `{doctype} [docname] field1=value1 field2=value2 ...`

Examples:
- `Purchase Order new supplier="Acme Corp" schedule_date=2026-04-30`
- `Sales Order SO-2026-00123 delivery_date=2026-05-15 status=To Deliver and Bill`

## Preconditions

- [ ] `ERPNEXT_BASE_URL`, `ERPNEXT_USERNAME`, `ERPNEXT_PASSWORD,ERPNEXT_API_KEY,ERPNEXT_API_SECRET` are set in environment
- [ ] DocType name is provided
- [ ] At least one field=value pair is provided
- [ ] For existing documents: `docname` is provided and known to exist

## Steps

### Step 1: Establish Session
Invoke `.rulesync/skills/erpnext-context/SKILL.md`. Confirm output shows `Ready: YES` before continuing.

### Step 2: Parse Arguments

Extract from `$ARGUMENTS`:
- `doctype` — first token (e.g. `Purchase Order`)
- `docname` — second token IF it does not contain `=` (e.g. `PO-2026-00001`); if absent, this is a new document
- `fields` — all remaining `key=value` pairs

If `doctype` is missing: STOP — report "DocType is required as the first argument."

### Step 3: Navigate to Form

**New document:**
```
page.goto(`${ERPNEXT_BASE_URL}/app/{doctype-slug}/new-{doctype-slug}-1`)
```
Wait for `.form-page` to be visible.

**Existing document:**
```
page.goto(`${ERPNEXT_BASE_URL}/app/{doctype-slug}/{docname}`)
```
Wait for `.form-page` to be visible. Confirm document title matches `docname`. If 404 or permission error: STOP.

### Step 4: Fill Fields

For each `field=value` pair:

1. Locate field by `data-fieldname="{field}"` within `.form-page`
2. Determine field type:
   - Input/Data: `page.fill('[data-fieldname="{field}"] input', value)`
   - Textarea: `page.fill('[data-fieldname="{field}"] textarea', value)`
   - Link: type partial value → wait for `.awesomplete ul li` → click match
   - Select: `page.selectOption('[data-fieldname="{field}"] select', value)`
   - Date: ensure format is `YYYY-MM-DD`, then fill input
   - Check: `page.check()` or `page.uncheck()` on checkbox input
3. If field not found after 5 seconds: STOP — report "Field '{field}' not found on {doctype} form. Verify fieldname spelling."
4. If Link field returns no dropdown results: STOP — report "No match for value '{value}' in Link field '{field}'."

### Step 5: Save

1. Click `[data-label="Save"]` within `.page-actions`
2. Wait for `.alert-success` visibility — timeout 8 seconds
3. If `.alert-danger` appears: read text, STOP — report exact error message
4. If `.msgprint` dialog appears: read message, click OK, check if success or error

### Step 6: Confirm and Report

Read document name from page title or URL after save.

## Output Format

```
Action: Form Fill / Edit
DocType: [doctype]
Document: [docname — new name if newly created]
Fields Set:
  {field1}: {value1}
  {field2}: {value2}
Result: [SUCCESS | FAILED | STOPPED]
Error: [exact error text, or "none"]
Next Step: [human action required, or "none"]
```

## Stop Conditions

- Session not established
- DocType not found (404 or permission denied)
- Required field has no matching value in system
- Validation error after Save
- Field not found on form
- Save confirmation toast not received within 8 seconds

// turbo
