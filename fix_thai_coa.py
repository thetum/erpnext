"""
ปรับปรุงผังบัญชีให้ถูกต้องตามมาตรฐานบัญชีไทย
- เพิ่มบัญชี VAT ซื้อ/ขาย
- เพิ่มบัญชีภาษีหัก ณ ที่จ่าย
- เพิ่มบัญชีภาษีเงินได้นิติบุคคล
- เพิ่มบัญชีค้างจ่าย/ค้างรับ/ล่วงหน้า
- เพิ่มสำรองตามกฎหมาย
- เพิ่มบัญชีประกันสังคม/กองทุนสำรองเลี้ยงชีพ
- เปลี่ยนชื่อ TDS Payable → ภาษีซื้อรอสรุป (ใช้ชั่วคราว)
"""
import urllib.request, urllib.error, json, time
from urllib.parse import quote

BASE    = "https://erp.chiangrai-nextstep.com"
AUTH    = "token 4739be7bcc70cb9:5cee8032426f370"
COMPANY = "Chiangrai Nextstep"
ABBR    = "CN"
CCY     = "THB"

HEADERS = {
    "Authorization": AUTH,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

created, skipped, errors = [], [], []


def api_get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def account_exists(name):
    try:
        api_get(f"/api/resource/Account/{quote(name)}")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def create_account(account_number, account_name, parent_account,
                   root_type, account_type="", is_group=0, report_type=None):
    full_name = f"{account_number} - {account_name} - {ABBR}"
    if account_exists(full_name):
        print(f"  SKIP  {full_name}")
        skipped.append(full_name)
        return full_name

    if report_type is None:
        report_type = "Balance Sheet" if root_type in ("Asset", "Liability", "Equity") else "Profit and Loss"

    payload = {
        "doctype": "Account",
        "account_name": account_name,
        "account_number": account_number,
        "parent_account": parent_account,
        "company": COMPANY,
        "root_type": root_type,
        "report_type": report_type,
        "account_type": account_type,
        "is_group": is_group,
        "account_currency": CCY,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/api/resource/Account",
        data=data, headers=HEADERS, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read().decode())
            name_out = resp["data"]["name"]
            print(f"  CREATE {name_out}")
            created.append(name_out)
            time.sleep(0.3)
            return name_out
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR  {full_name}: {e.code} {body[:200]}")
        errors.append(f"{full_name}: {body[:200]}")
        return None


def rename_account(old_name, new_account_name):
    """Update account_name of existing account via PUT."""
    if not account_exists(old_name):
        print(f"  RENAME SKIP (not found): {old_name}")
        return
    payload = json.dumps({"account_name": new_account_name}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/resource/Account/{quote(old_name)}",
        data=payload, headers=HEADERS, method="PUT"
    )
    try:
        with urllib.request.urlopen(req) as r:
            print(f"  RENAME {old_name} → {new_account_name}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  RENAME ERROR {old_name}: {e.code} {body[:200]}")


# ─────────────────────────────────────────────
print("\n== 1. ภาษีซื้อ / ภาษีขาย (VAT) ==")

create_account(
    "1510", "ภาษีซื้อ",
    "1500 - Tax Assets - CN",
    root_type="Asset", account_type="Tax",
)
create_account(
    "1511", "ภาษีซื้อยังไม่ถึงกำหนด",
    "1500 - Tax Assets - CN",
    root_type="Asset", account_type="Tax",
)
create_account(
    "1512", "ภาษีซื้อไม่ขอคืน",
    "1500 - Tax Assets - CN",
    root_type="Asset", account_type="Tax",
)

create_account(
    "2320", "ภาษีขาย",
    "2300 - Duties and Taxes - CN",
    root_type="Liability", account_type="Tax",
)

# ─────────────────────────────────────────────
print("\n== 2. ภาษีหัก ณ ที่จ่าย ==")

create_account(
    "1530", "ภาษีถูกหัก ณ ที่จ่าย",
    "1500 - Tax Assets - CN",
    root_type="Asset", account_type="Tax",
)

wht_group = create_account(
    "2330", "ภาษีหัก ณ ที่จ่ายค้างจ่าย",
    "2300 - Duties and Taxes - CN",
    root_type="Liability", account_type="Tax", is_group=1,
)
if wht_group:
    for num, rate in [("2331","1%"),("2332","2%"),("2333","3%"),
                      ("2334","5%"),("2335","10%"),("2336","15%")]:
        create_account(
            num, f"ภาษีหัก ณ ที่จ่าย {rate}",
            wht_group,
            root_type="Liability", account_type="Tax",
        )

# ─────────────────────────────────────────────
print("\n== 3. ภาษีเงินได้นิติบุคคล (CIT) ==")

create_account(
    "2340", "ภาษีเงินได้นิติบุคคลค้างจ่าย",
    "2300 - Duties and Taxes - CN",
    root_type="Liability", account_type="Tax",
)
create_account(
    "5224", "ภาษีเงินได้นิติบุคคล",
    "5200 - Indirect Expenses - CN",
    root_type="Expense", report_type="Profit and Loss",
)

# ─────────────────────────────────────────────
print("\n== 4. ค่าใช้จ่ายค้างจ่าย / รายได้รับล่วงหน้า ==")

accrued_group = create_account(
    "2500", "ค่าใช้จ่ายค้างจ่าย",
    "2100-2400 - Current Liabilities - CN",
    root_type="Liability", is_group=1,
)
if accrued_group:
    for num, name in [
        ("2510", "เงินเดือนค้างจ่าย"),
        ("2520", "ประกันสังคมค้างจ่าย"),
        ("2530", "กองทุนสำรองเลี้ยงชีพค้างจ่าย"),
        ("2540", "ค่าใช้จ่ายค้างจ่ายอื่น"),
    ]:
        create_account(num, name, accrued_group, root_type="Liability")

create_account(
    "2600", "รายได้รับล่วงหน้า",
    "2100-2400 - Current Liabilities - CN",
    root_type="Liability",
)

# ─────────────────────────────────────────────
print("\n== 5. ค่าใช้จ่ายจ่ายล่วงหน้า / รายได้ค้างรับ ==")

create_account(
    "1660", "ค่าใช้จ่ายจ่ายล่วงหน้า",
    "1100-1600 - Current Assets - CN",
    root_type="Asset",
)
create_account(
    "1670", "รายได้ค้างรับ",
    "1100-1600 - Current Assets - CN",
    root_type="Asset",
)

# ─────────────────────────────────────────────
print("\n== 6. สำรองตามกฎหมาย (Legal Reserve) ==")

create_account(
    "3500", "สำรองตามกฎหมาย",
    "3000 - Equity - CN",
    root_type="Equity", account_type="Equity",
)

# ─────────────────────────────────────────────
print("\n== 7. ประกันสังคม / กองทุนสำรองเลี้ยงชีพ ==")

create_account(
    "5222", "ประกันสังคม",
    "5200 - Indirect Expenses - CN",
    root_type="Expense", report_type="Profit and Loss",
)
create_account(
    "5223", "กองทุนสำรองเลี้ยงชีพ",
    "5200 - Indirect Expenses - CN",
    root_type="Expense", report_type="Profit and Loss",
)

# ─────────────────────────────────────────────
print("\n== 8. รายได้อื่น (เพิ่มใน Indirect Income) ==")

for num, name in [
    ("4210", "ดอกเบี้ยรับ"),
    ("4220", "กำไรจากอัตราแลกเปลี่ยน"),
    ("4230", "รายได้อื่น"),
]:
    create_account(
        num, name,
        "4200 - Indirect Income - CN",
        root_type="Income", report_type="Profit and Loss",
    )

# ─────────────────────────────────────────────
print("\n== 9. เปลี่ยนชื่อ TDS Payable ==")
rename_account("2310 - TDS Payable - CN", "ภาษีหัก ณ ที่จ่ายนำส่ง (เก่า)")

# ─────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"สรุป: สร้างใหม่ {len(created)} | ข้ามซ้ำ {len(skipped)} | ผิดพลาด {len(errors)}")
if errors:
    print("Errors:")
    for e in errors:
        print(f"  - {e}")
