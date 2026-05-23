#!/usr/bin/env python3
"""Clean up duplicate/wrong-named accounts and restore correct ones."""

import openpyxl
import requests
import json
import time

BASE_URL = "https://erp.chiangrai-nextstep.com"
HEADERS = {"Authorization": "token 4739be7bcc70cb9:5cee8032426f370"}
COMPANY = "Chiangrai Nextstep"
ABBR = "CN"

ROOT_TYPE_MAP = {
    "สินทรัพย์": "Asset",
    "หนี้สิน": "Liability",
    "ส่วนของผู้ถือหุ้น": "Equity",
    "รายได้": "Income",
    "ค่าใช้จ่าย": "Expense",
}


def api_get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def api_post(path, payload):
    r = requests.post(f"{BASE_URL}{path}", json=payload, headers=HEADERS, timeout=30)
    return r


def api_put(name, payload):
    r = requests.put(
        f"{BASE_URL}/api/resource/Account/{requests.utils.quote(name)}",
        json=payload, headers=HEADERS, timeout=30,
    )
    return r


def api_delete(name):
    r = requests.delete(
        f"{BASE_URL}/api/resource/Account/{requests.utils.quote(name)}",
        headers=HEADERS, timeout=30,
    )
    return r


def get_all_accounts():
    r = api_get("/api/resource/Account", {
        "filters": json.dumps([["company", "=", COMPANY]]),
        "fields": json.dumps(["name", "account_name", "is_group", "parent_account",
                               "account_type", "root_type", "account_currency", "lft", "rgt"]),
        "limit": 500,
        "order_by": "lft asc",
    })
    return {a["name"]: a for a in r.get("data", [])}


def read_excel(path):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    accounts = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 2 or not any(row):
            continue
        code, name, parent, root_type_th, acc_type, currency, is_group_th, note = row
        name_clean = name.strip() if name else ""
        if not name_clean:
            continue
        code_str = str(code).strip() if code else ""
        # Build the expected ERPNext full name
        if code_str:
            expected_name = f"{code_str} - {name_clean} - {ABBR}"
            account_name = f"{code_str} - {name_clean}"
        else:
            expected_name = f"{name_clean} - {ABBR}"
            account_name = name_clean

        accounts.append({
            "code": code_str,
            "name_clean": name_clean,
            "account_name": account_name,
            "expected_name": expected_name,
            "parent": parent.strip() if parent else "",
            "root_type": ROOT_TYPE_MAP.get(root_type_th, ""),
            "account_type": acc_type or "",
            "currency": currency or "THB",
            "is_group": 1 if is_group_th == "ใช่" else 0,
        })
    return accounts


def main():
    print("=" * 60)
    print("COA Cleanup & Fix")
    print("=" * 60)

    excel_accounts = read_excel("ผังบัญชี_โรงงานสุรา.xlsx")
    expected_names = {a["expected_name"] for a in excel_accounts}
    excel_by_name = {a["expected_name"]: a for a in excel_accounts}

    print(f"Expected accounts from Excel: {len(expected_names)}")

    existing = get_all_accounts()
    print(f"Current accounts in ERPNext: {len(existing)}")

    # Root account names (system-managed, never delete)
    root_accounts = {
        "Application of Funds (Assets) - CN",
        "Source of Funds (Liabilities) - CN",
        "Equity - CN",
        "Income - CN",
        "Expenses - CN",
    }

    # --- Step 1: Delete wrong-named accounts (created by buggy script) ---
    print("\n--- Step 1: Delete wrong-named accounts ---")
    wrong_accounts = []
    for name in existing:
        if name in root_accounts:
            continue
        if name not in expected_names:
            wrong_accounts.append(name)

    # Sort leaf nodes first (rgt - lft == 1 means leaf)
    def sort_key(name):
        acc = existing[name]
        return -(acc.get("rgt", 0) - acc.get("lft", 0))

    wrong_accounts.sort(key=sort_key)

    deleted = 0
    skipped_wrong = []
    for name in wrong_accounts:
        r = api_delete(name)
        if r.status_code == 202:
            print(f"  DELETED wrong: {name}")
            deleted += 1
        else:
            err = r.json().get("exception", r.text[:100])
            print(f"  SKIP (cannot delete): {name} — {err[:80]}")
            skipped_wrong.append(name)
        time.sleep(0.2)

    # --- Step 2: Create missing correct-named accounts ---
    print(f"\n--- Step 2: Create missing accounts ---")
    existing = get_all_accounts()  # refresh

    created = 0
    for acc in excel_accounts:
        en = acc["expected_name"]
        if en in existing:
            continue
        # Root accounts cannot be created via API (they are system roots)
        if acc["parent"] == "":
            print(f"  SKIP root (system-managed): {en}")
            continue

        payload = {
            "doctype": "Account",
            "account_name": acc["account_name"],
            "company": COMPANY,
            "is_group": acc["is_group"],
            "account_currency": acc["currency"],
        }
        if acc["root_type"]:
            payload["root_type"] = acc["root_type"]
        if acc["account_type"]:
            payload["account_type"] = acc["account_type"]
        if acc["parent"]:
            payload["parent_account"] = acc["parent"]

        r = api_post("/api/resource/Account", payload)
        if r.status_code in (200, 201):
            print(f"  CREATED: {en}")
            created += 1
            existing[en] = {"name": en, "is_group": acc["is_group"]}
        else:
            print(f"  ERROR: {en} — {r.status_code} {r.text[:150]}")
        time.sleep(0.2)

    # --- Step 3: Fix is_group for accounts that changed ---
    print(f"\n--- Step 3: Fix is_group mismatches ---")
    existing = get_all_accounts()
    fixed = 0
    for acc in excel_accounts:
        en = acc["expected_name"]
        if en not in existing:
            continue
        ex = existing[en]
        if int(ex.get("is_group", 0)) != acc["is_group"]:
            r = api_put(en, {"is_group": acc["is_group"]})
            if r.status_code == 200:
                print(f"  FIXED is_group: {en} → {acc['is_group']}")
                fixed += 1
            else:
                print(f"  ERROR fixing {en}: {r.status_code} {r.text[:150]}")

    print(f"\n{'=' * 60}")
    print(f"Deleted wrong accounts: {deleted}")
    if skipped_wrong:
        print(f"Could not delete (has transactions): {len(skipped_wrong)}")
        for n in skipped_wrong:
            print(f"  - {n}")
    print(f"Created missing: {created}")
    print(f"Fixed is_group: {fixed}")


if __name__ == "__main__":
    main()
