#!/usr/bin/env python3
"""Migrate ERPNext Chart of Accounts to new structure from Excel."""

import openpyxl
import requests
import json
import time

BASE_URL = "https://erp.chiangrai-nextstep.com"
HEADERS = {"Authorization": "token 4739be7bcc70cb9:5cee8032426f370"}
COMPANY = "Chiangrai Nextstep"
ABBR = "CN"

ROOT_SYSTEM = {
    f"Application of Funds (Assets) - {ABBR}",
    f"Source of Funds (Liabilities) - {ABBR}",
    f"Equity - {ABBR}",
    f"Income - {ABBR}",
    f"Expenses - {ABBR}",
}


def get(path, params=None):
    r = requests.get(f"{BASE_URL}{path}", params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def post(path, payload):
    return requests.post(f"{BASE_URL}{path}", json=payload, headers=HEADERS, timeout=30)


def put(name, payload):
    return requests.put(
        f"{BASE_URL}/api/resource/Account/{requests.utils.quote(name)}",
        json=payload, headers=HEADERS, timeout=30,
    )


def delete(name):
    return requests.delete(
        f"{BASE_URL}/api/resource/Account/{requests.utils.quote(name)}",
        headers=HEADERS, timeout=30,
    )


def get_all_accounts():
    r = get("/api/resource/Account", {
        "filters": json.dumps([["company", "=", COMPANY]]),
        "fields": json.dumps(["name", "is_group", "parent_account", "lft", "rgt"]),
        "limit": 500,
        "order_by": "lft asc",
    })
    return {a["name"]: a for a in r.get("data", [])}


def read_excel(path):
    wb = openpyxl.load_workbook(path)
    ws = wb["ERPNext Import"]
    accounts = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 2 or not any(row):
            continue
        code, name, parent, root_type, acc_type, currency, is_group, notes = row
        if not name:
            continue
        code_str = str(int(code)) if isinstance(code, float) else (str(code).strip() if code else "")
        name_clean = name.strip()
        account_name = f"{code_str} - {name_clean}" if code_str else name_clean
        expected_name = f"{account_name} - {ABBR}"
        accounts.append({
            "code": code_str,
            "name_clean": name_clean,
            "account_name": account_name,
            "expected_name": expected_name,
            "parent": parent.strip() if parent else "",
            "root_type": root_type or "",
            "account_type": acc_type or "",
            "currency": currency or "THB",
            "is_group": 1 if is_group == 1 else 0,
        })
    return accounts


def main():
    print("=" * 60)
    print("ERPNext COA Migration")
    print("=" * 60)

    excel_accounts = read_excel("ผังบัญชี_โรงงานสุรา_แก้ไขแล้ว.xlsx")
    expected = {a["expected_name"]: a for a in excel_accounts}
    print(f"New COA accounts: {len(expected)}")

    existing = get_all_accounts()
    print(f"Current ERPNext accounts: {len(existing)}")

    # ── Step 1: Create new accounts (parent before child) ──────────────
    print("\n--- Step 1: Create missing accounts ---")
    created = updated = skipped = errors = 0

    for acc in excel_accounts:
        en = acc["expected_name"]

        # Root accounts already exist (system-managed)
        if not acc["parent"]:
            skipped += 1
            continue

        if en in existing:
            # Check if is_group needs update
            if int(existing[en].get("is_group", 0)) != acc["is_group"]:
                r = put(en, {"is_group": acc["is_group"]})
                if r.status_code == 200:
                    print(f"  UPDATED is_group: {en} → {acc['is_group']}")
                    updated += 1
                else:
                    print(f"  ERROR updating {en}: {r.text[:120]}")
                    errors += 1
            else:
                skipped += 1
            continue

        payload = {
            "doctype": "Account",
            "account_name": acc["account_name"],
            "company": COMPANY,
            "is_group": acc["is_group"],
            "account_currency": acc["currency"],
            "parent_account": acc["parent"],
        }
        if acc["root_type"]:
            payload["root_type"] = acc["root_type"]
        if acc["account_type"]:
            payload["account_type"] = acc["account_type"]

        r = post("/api/resource/Account", payload)
        if r.status_code in (200, 201):
            print(f"  CREATED: {en}")
            created += 1
            existing[en] = {"name": en, "is_group": acc["is_group"]}
        else:
            err = r.json().get("exception", r.text)[:150]
            print(f"  ERROR: {en}\n         {err}")
            errors += 1
        time.sleep(0.15)

    print(f"\nStep 1 done — Created: {created} | Updated: {updated} | Skipped: {skipped} | Errors: {errors}")

    # ── Step 2: Delete old accounts not in new COA ─────────────────────
    print("\n--- Step 2: Delete old accounts ---")
    existing = get_all_accounts()

    to_delete = [
        name for name in existing
        if name not in expected and name not in ROOT_SYSTEM
    ]

    # Delete leaves first (largest lft-rgt gap = deepest node has rgt-lft==1)
    to_delete.sort(key=lambda n: -(existing[n].get("rgt", 0) - existing[n].get("lft", 0)))

    deleted = skipped_del = 0
    cannot_delete = []

    for name in to_delete:
        r = delete(name)
        if r.status_code == 202:
            print(f"  DELETED: {name}")
            deleted += 1
        else:
            reason = r.json().get("exc_type", "")
            if "ChildExists" in reason:
                skipped_del += 1  # will retry after children are deleted
            else:
                cannot_delete.append((name, reason))
        time.sleep(0.15)

    # Retry parents whose children are now gone
    for name in to_delete:
        if name in [n for n, _ in cannot_delete]:
            continue
        if name in existing:
            r = delete(name)
            if r.status_code == 202:
                print(f"  DELETED (retry): {name}")
                deleted += 1
            time.sleep(0.15)

    print(f"\nStep 2 done — Deleted: {deleted}")
    if cannot_delete:
        print(f"Cannot delete (has transactions — manual action needed):")
        for name, reason in cannot_delete:
            print(f"  ⚠ {name}  [{reason}]")

    # ── Summary ────────────────────────────────────────────────────────
    existing = get_all_accounts()
    print(f"\n{'=' * 60}")
    print(f"Final account count in ERPNext: {len(existing)}")
    print(f"Expected from new COA: {len(expected)}")


if __name__ == "__main__":
    main()
