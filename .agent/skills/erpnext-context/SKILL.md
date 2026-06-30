---
name: erpnext-context
description: >-
  Load ERPNext environment variables, perform login, and detect current page
  state before any ERPNext task
---
# Skill: ERPNext Context

Reads environment configuration, establishes an authenticated Playwright session, and identifies the current page state. This skill MUST be invoked at the start of every ERPNext session before any navigation or form interaction.

## When to Use

- At the beginning of every ERPNext agent task
- When the agent has been idle and page state is unknown
- When a navigation error or blank page is encountered and session may have expired

## Steps (Execute In Order)

### 1. Read Environment Variables

Read these three variables from the environment — do NOT hardcode values:

| Variable | Purpose |
|---|---|
| `ERPNEXT_BASE_URL` | Base URL of ERPNext instance, e.g. `https://erp.example.com` — no trailing slash |
| `ERPNEXT_USERNAME` | Login email or username |
| `ERPNEXT_PASSWORD` | Login password |

If any variable is missing or empty: STOP — report exactly which variable is unset. Do not attempt login.

### 2. Check Current Page State

Before navigating to login, check if a Playwright session is already active:

- If current URL contains `${ERPNEXT_BASE_URL}/app`: session is active — skip login, proceed to step 4
- If current URL is `${ERPNEXT_BASE_URL}/login` or Playwright has no active page: proceed to step 3
- If current URL is any other domain: STOP — report "Playwright session pointed at unexpected URL: {url}"

### 3. Perform Login

```
1. page.goto(`${ERPNEXT_BASE_URL}/login`)
2. waitForSelector('#login_email', { state: 'visible', timeout: 10000 })
3. page.fill('#login_email', ERPNEXT_USERNAME)
4. page.fill('#login_password', ERPNEXT_PASSWORD)
5. page.click('[data-label="Login"]')
6. waitForURL(`${ERPNEXT_BASE_URL}/app**`, { timeout: 10000 })
```

If step 6 times out (URL stays at `/login`):
- Check for `.alert-danger` or `.msgprint` error — extract text
- STOP — report: "Login failed: {error text}. Verify ERPNEXT_USERNAME and ERPNEXT_PASSWORD."

### 4. Detect Current Page State

After confirmed login, identify the current page context:

| Indicator | Page State |
|---|---|
| URL matches `/app/{doctype}/{docname}` | Form view — single document open |
| URL matches `/app/{doctype}` | List view — DocType list |
| URL matches `/app/query-report/{name}` | Report view |
| URL matches `/app` or `/app/home` | Desk / Home |
| `.frappe-toast` visible | Pending notification — read and include in output |

### 5. Check Session Validity

- Confirm `.navbar-brand` or `#navbar-main` is visible — confirms desk is loaded
- If not visible after `/app` URL is confirmed: reload once, re-check
- If still not visible: re-run login sequence (step 3) once
- If login fails second time: STOP — report "Session could not be established after two attempts"

## Output Format

```
Environment:
  ERPNEXT_BASE_URL: [value or MISSING]
  ERPNEXT_USERNAME: [value or MISSING]
  ERPNEXT_PASSWORD: [SET or MISSING — never print actual value]

Session Status: [ACTIVE | LOGGED_IN | FAILED]
Current Page State: [Form: {doctype}/{docname} | List: {doctype} | Report: {name} | Desk | Unknown]
Pending Notifications: [text of any visible toast, or "none"]
Ready: [YES | NO — reason if NO]
```

## Usage Notes

- ERPNEXT_PASSWORD must never appear in any output — always write "SET" or "MISSING" only
- If `ERPNEXT_BASE_URL` has a trailing slash, strip it before constructing URLs
- This skill does not perform any form actions — its scope is session establishment and state detection only
- If the system shows a "Tour" or onboarding dialog after login: dismiss it by pressing Escape before reporting Ready: YES
