"""
เพิ่มผังบัญชีสำหรับโรงงานผลิตสุราใน ERPNext
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


def account_exists(name):
    req = urllib.request.Request(
        f"{BASE}/api/resource/Account/{quote(name)}", headers=HEADERS
    )
    try:
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def create(number, name, parent, root_type, account_type="", is_group=0):
    full_name = f"{number} - {name} - {ABBR}"
    if account_exists(full_name):
        print(f"  SKIP   {full_name}")
        skipped.append(full_name)
        return full_name

    report_type = "Balance Sheet" if root_type in ("Asset", "Liability", "Equity") else "Profit and Loss"
    payload = json.dumps({
        "doctype": "Account",
        "account_name": name,
        "account_number": number,
        "parent_account": parent,
        "company": COMPANY,
        "root_type": root_type,
        "report_type": report_type,
        "account_type": account_type,
        "is_group": is_group,
        "account_currency": CCY,
    }).encode()

    req = urllib.request.Request(
        f"{BASE}/api/resource/Account",
        data=payload, headers=HEADERS, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            name_out = json.loads(r.read().decode())["data"]["name"]
            print(f"  CREATE {name_out}")
            created.append(name_out)
            time.sleep(0.25)
            return name_out
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR  {full_name}: {e.code} {body[:200]}")
        errors.append(f"{full_name}: {body[:200]}")
        return None


# ──────────────────────────────────────────────────────────────
print("\n== 1. สินค้าคงเหลือ — วัตถุดิบ / WIP / สำเร็จรูป ==")

# กลุ่มวัตถุดิบ ใต้ 1400 - Stock Assets
raw_grp = create("1411", "วัตถุดิบ", "1400 - Stock Assets - CN",
                 root_type="Asset", account_type="Stock", is_group=1)
if raw_grp:
    create("1411-1", "ข้าว/มอลต์/สารหมัก",      raw_grp, "Asset", "Stock")
    create("1411-2", "สารปรุงแต่งและสารเคมี",    raw_grp, "Asset", "Stock")
    create("1411-3", "เชื้อเพลิงโรงงาน",          raw_grp, "Asset", "Stock")

# บรรจุภัณฑ์
create("1412", "บรรจุภัณฑ์", "1400 - Stock Assets - CN",
       root_type="Asset", account_type="Stock")

# งานระหว่างผลิต
wip_grp = create("1420", "งานระหว่างผลิต", "1400 - Stock Assets - CN",
                 root_type="Asset", account_type="Stock", is_group=1)
if wip_grp:
    create("1421", "สุราระหว่างหมัก",   wip_grp, "Asset", "Stock")
    create("1422", "สุราระหว่างกลั่น",  wip_grp, "Asset", "Stock")
    create("1423", "สุราระหว่างบ่ม",    wip_grp, "Asset", "Stock")

# สินค้าสำเร็จรูป
fg_grp = create("1430", "สินค้าสำเร็จรูป — สุรา", "1400 - Stock Assets - CN",
                root_type="Asset", account_type="Stock", is_group=1)
if fg_grp:
    create("1431", "สุรากลั่น",              fg_grp, "Asset", "Stock")
    create("1432", "สุราหมัก",               fg_grp, "Asset", "Stock")
    create("1433", "ผลพลอยได้ (กากสุรา)",   fg_grp, "Asset", "Stock")

# ──────────────────────────────────────────────────────────────
print("\n== 2. สินทรัพย์ไม่มีตัวตน — ใบอนุญาต ==")

intangible_grp = create("1810", "สินทรัพย์ไม่มีตัวตน", "1800 - Investments - CN",
                         root_type="Asset", is_group=1)
if intangible_grp:
    create("1811", "ใบอนุญาตผลิตสุรา",          intangible_grp, "Asset")
    create("1812", "ค่าใบอนุญาตสะสมตัดจำหน่าย", intangible_grp, "Asset",
           account_type="Accumulated Depreciation")

# ──────────────────────────────────────────────────────────────
print("\n== 3. ภาษีสรรพสามิต (Excise Tax) ==")

create("2350", "ภาษีสรรพสามิตค้างจ่าย",
       "2300 - Duties and Taxes - CN",
       root_type="Liability", account_type="Tax")

create("2351", "กองทุนสุราค้างจ่าย",
       "2300 - Duties and Taxes - CN",
       root_type="Liability", account_type="Tax")

create("2352", "ค่าธรรมเนียมใบอนุญาตค้างจ่าย",
       "2300 - Duties and Taxes - CN",
       root_type="Liability")

# ──────────────────────────────────────────────────────────────
print("\n== 4. ต้นทุนการผลิตทางตรง ==")

# ค่าแรงทางตรง ใต้ 5100 Direct Expenses
create("5120", "ค่าแรงทางตรง", "5100 - Direct Expenses - CN",
       root_type="Expense")

# ภาษีสรรพสามิต — ต้นทุนหลัก ใต้ Direct Expenses
create("5130", "ภาษีสรรพสามิต", "5100 - Direct Expenses - CN",
       root_type="Expense")
create("5131", "กองทุนสุรา", "5100 - Direct Expenses - CN",
       root_type="Expense")
create("5132", "ค่าธรรมเนียมใบอนุญาตสุรา", "5100 - Direct Expenses - CN",
       root_type="Expense")

# ──────────────────────────────────────────────────────────────
print("\n== 5. โสหุ้ยการผลิต (Manufacturing Overhead) ==")

mfg_grp = create("5140", "โสหุ้ยการผลิต", "5100 - Direct Expenses - CN",
                 root_type="Expense", is_group=1)
if mfg_grp:
    create("5141", "ค่าไฟฟ้าโรงงาน",             mfg_grp, "Expense")
    create("5142", "ค่าน้ำโรงงาน",                mfg_grp, "Expense")
    create("5143", "ค่าเสื่อมราคาเครื่องจักร",    mfg_grp, "Expense",
           account_type="Depreciation")
    create("5144", "ค่าซ่อมบำรุงเครื่องจักร",     mfg_grp, "Expense")
    create("5145", "ค่าแรงทางอ้อม",               mfg_grp, "Expense")
    create("5146", "วัสดุโรงงานสิ้นเปลือง",       mfg_grp, "Expense")
    create("5147", "ค่าประกันภัยโรงงาน",          mfg_grp, "Expense")

# ──────────────────────────────────────────────────────────────
print("\n== 6. ค่าใช้จ่ายอื่นที่เกี่ยวข้อง ==")

create("5225", "ค่าธรรมเนียมและใบอนุญาตประจำปี",
       "5200 - Indirect Expenses - CN", root_type="Expense")
create("5226", "ค่าตรวจวิเคราะห์คุณภาพสุรา",
       "5200 - Indirect Expenses - CN", root_type="Expense")
create("5227", "ค่าขนส่งสินค้า",
       "5200 - Indirect Expenses - CN", root_type="Expense",
       account_type="Chargeable")

# ──────────────────────────────────────────────────────────────
print("\n== 7. รายได้จากการขายสุรา ==")

create("4111", "รายได้ขายสุรากลั่น",
       "4100 - Direct Income - CN", root_type="Income")
create("4112", "รายได้ขายสุราหมัก",
       "4100 - Direct Income - CN", root_type="Income")
create("4113", "รายได้ขายผลพลอยได้",
       "4100 - Direct Income - CN", root_type="Income")

# ──────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"สรุป: สร้างใหม่ {len(created)} | ข้ามซ้ำ {len(skipped)} | ผิดพลาด {len(errors)}")
if errors:
    print("Errors:")
    for e in errors:
        print(f"  - {e}")
