#!/usr/bin/env python3
"""Import/sync Chart of Accounts from Excel into ERPNext via REST API."""

import openpyxl
import requests
import json
import time

BASE_URL = "https://erp.chiangrai-nextstep.com"
API_KEY = "4739be7bcc70cb9"
API_SECRET = "5cee8032426f370"
COMPANY = "Chiangrai Nextstep"
HEADERS = {"Authorization": f"token {API_KEY}:{API_SECRET}"}

ROOT_TYPE_MAP = {
    "สินทรัพย์": "Asset",
    "หนี้สิน": "Liability",
    "ส่วนของผู้ถือหุ้น": "Equity",
    "รายได้": "Income",
    "ค่าใช้จ่าย": "Expense",
}


def get_all_existing_accounts():
    accounts = {}
    limit = 500
    resp = requests.get(
        f"{BASE_URL}/api/resource/Account",
        params={
            "filters": json.dumps([["company", "=", COMPANY]]),
            "fields": json.dumps(["name", "account_name", "is_group", "parent_account",
                                   "account_type", "root_type", "account_currency"]),
            "limit": limit,
            "order_by": "lft asc",
        },
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    for acc in resp.json().get("data", []):
        accounts[acc["name"]] = acc
    print(f"Existing accounts in ERPNext: {len(accounts)}")
    return accounts


def read_excel(path):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    accounts = []
    headers = None
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # title row
        if i == 1:
            headers = row
            continue
        if not any(row):
            continue
        code, name, parent, root_type_th, acc_type, currency, is_group_th, note = row
        if not name:
            continue
        # Strip leading spaces from name
        name_clean = name.strip() if name else ""
        is_group = 1 if is_group_th == "ใช่" else 0
        root_type = ROOT_TYPE_MAP.get(root_type_th, "")
        accounts.append({
            "code": str(code).strip() if code else "",
            "name_clean": name_clean,
            "parent": parent.strip() if parent else "",
            "root_type": root_type,
            "account_type": acc_type or "",
            "currency": currency or "THB",
            "is_group": is_group,
        })
    print(f"Accounts in Excel: {len(accounts)}")
    return accounts


def build_erpnext_name(name_clean, abbr="CN"):
    return f"{name_clean} - {abbr}"


def create_account(acc, existing):
    name_clean = acc["name_clean"]
    erpnext_name = build_erpnext_name(name_clean)

    # Build payload
    payload = {
        "doctype": "Account",
        "account_name": name_clean,
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

    resp = requests.post(
        f"{BASE_URL}/api/resource/Account",
        json=payload,
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        print(f"  CREATED: {erpnext_name}")
        return True
    else:
        print(f"  ERROR creating {erpnext_name}: {resp.status_code} {resp.text[:200]}")
        return False


def update_account(erpnext_name, updates):
    resp = requests.put(
        f"{BASE_URL}/api/resource/Account/{requests.utils.quote(erpnext_name)}",
        json=updates,
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code == 200:
        print(f"  UPDATED: {erpnext_name} → {updates}")
        return True
    else:
        print(f"  ERROR updating {erpnext_name}: {resp.status_code} {resp.text[:200]}")
        return False


def delete_account(erpnext_name):
    resp = requests.delete(
        f"{BASE_URL}/api/resource/Account/{requests.utils.quote(erpnext_name)}",
        headers=HEADERS,
        timeout=30,
    )
    if resp.status_code == 202:
        print(f"  DELETED: {erpnext_name}")
        return True
    else:
        print(f"  ERROR deleting {erpnext_name}: {resp.status_code} {resp.text[:200]}")
        return False


def main():
    print("=" * 60)
    print("ERPNext Chart of Accounts Importer")
    print("=" * 60)

    existing = get_all_existing_accounts()
    excel_accounts = read_excel("ผังบัญชี_โรงงานสุรา.xlsx")

    # Build set of names expected from Excel
    excel_names = set()
    for acc in excel_accounts:
        excel_names.add(build_erpnext_name(acc["name_clean"]))

    # Accounts to delete (in ERPNext but not in Excel, excluding root system accounts)
    system_roots = {
        "Application of Funds (Assets) - CN",
        "Source of Funds (Liabilities) - CN",
        "Equity - CN",
        "Income - CN",
        "Expenses - CN",
    }
    # Find accounts removed from Excel (like 2331-2336)
    to_delete = []
    for name in existing:
        if name not in excel_names and name not in system_roots:
            # Check if it's a company account
            acc = existing[name]
            # Only delete sub-accounts we manage (skip system-level ones)
            if acc.get("root_type"):  # has root_type = real account
                to_delete.append(name)

    print(f"\nAccounts to delete (removed from Excel): {len(to_delete)}")
    for n in to_delete:
        print(f"  - {n}")

    print(f"\n--- Step 1: Delete removed accounts ---")
    for name in to_delete:
        delete_account(name)
        time.sleep(0.3)

    # Refresh existing after deletes
    existing = get_all_existing_accounts()

    print(f"\n--- Step 2: Create/Update accounts from Excel ---")
    created = 0
    updated = 0
    skipped = 0

    for acc in excel_accounts:
        erpnext_name = build_erpnext_name(acc["name_clean"])

        if erpnext_name in existing:
            ex = existing[erpnext_name]
            updates = {}
            # Check if is_group changed
            if int(ex.get("is_group", 0)) != acc["is_group"]:
                updates["is_group"] = acc["is_group"]
            # Check account_type
            if acc["account_type"] and ex.get("account_type") != acc["account_type"]:
                updates["account_type"] = acc["account_type"]
            if updates:
                if update_account(erpnext_name, updates):
                    updated += 1
            else:
                skipped += 1
        else:
            if create_account(acc, existing):
                created += 1
                existing[erpnext_name] = {"name": erpnext_name, "is_group": acc["is_group"]}
            time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"Done! Created: {created} | Updated: {updated} | Skipped (unchanged): {skipped}")
    print(f"Deleted: {len(to_delete)}")


if __name__ == "__main__":
    main()
