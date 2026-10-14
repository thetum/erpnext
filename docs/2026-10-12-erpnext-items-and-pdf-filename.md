# สรุปงาน ERPNext — 2026-10-12

ทำผ่าน REST API ของ `https://erp.chiangrai-nextstep.com` โดยตรง (ไม่ผ่านหน้าเว็บ) ใช้ API key/secret จาก `.env`

## 1. เพิ่ม Item ใหม่ 2 รายการ (Services)

| Item Code | Item Name | Item Group | UOM | ราคา |
|---|---|---|---|---|
| `LABEL-SUBMIT-COORD` | Label submission & coordination | Services | SKU | 5,000 บาท/SKU |
| `SAMPLE-PROD-PREP` | Sample production & preparation | Services | SKU | 5,000 บาท/SKU |

รายละเอียด (เก็บไว้ใน field Description ของแต่ละ item):

- **Label submission & coordination**: ครอบคลุมการตรวจเอกสาร, ยื่นแบบ, ประสานงาน, ติดตาม และแก้ไขในขอบเขตปกติ
- **Sample production & preparation**: ครอบคลุมการผลิตตัวอย่าง, ขวด, บรรจุ และการเตรียมเพื่อส่งตรวจ

ขั้นตอนที่ทำ:

1. สร้าง UOM ใหม่ชื่อ `SKU` (ยังไม่มีในระบบ) เพื่อให้ตรงกับหน่วยราคาที่ลูกค้าระบุ
2. สร้าง Item ทั้งสองตัวแบบ non-stock (`is_stock_item = 0`), `item_group = Services`, `stock_uom = SKU`
3. เพิ่มราคาผ่าน **Item Price** แยก (ไม่ใส่ `standard_rate` ตรงใน Item) บน price list **"ราคาปลีก (Retail Price)"** ที่ 5,000 บาท/SKU

**เหตุผลที่ไม่ใส่ราคาตรงใน Item ตอนสร้าง:** พบว่า price list default ของระบบ (`Standard Selling`) ถูก disable ไว้ (`enabled = 0`) การสร้าง Item พร้อม `standard_rate` จะไป trigger auto-create Item Price บน price list ตัวนี้ทันที ทำให้ validation error และ rollback การสร้าง item ทั้งหมด จึงต้องสร้าง item ก่อน แล้วค่อยเพิ่มราคาแยกบน price list ที่เปิดใช้งานอยู่

**ค้างไว้ให้พิจารณา:** ถ้าต้องการให้ auto-fill ราคาตอนออกเอกสารขายทำงานปกติ (อิง default price list) ต้องเปิดใช้งาน `Standard Selling` กลับ (ปัจจุบันยังปิดอยู่) หรือไม่ก็ต้องเลือก price list "ราคาปลีก (Retail Price)" เองทุกครั้งตอนออกเอกสาร

## 2. แก้ชื่อไฟล์ PDF ตอน Print ให้เป็นเลขที่เอกสาร

> **ยกเลิกแล้ว (2026-10-14):** Property Setter `title_field = "name"` ทำให้หน้า list ของทั้ง 7 DocType ไม่แสดงข้อมูล จึงลบออกและไปตั้งชื่อไฟล์ใน Print Format แทน ดู [2026-10-14-fix-list-view-and-pdf-title.md](2026-10-14-fix-list-view-and-pdf-title.md)

**ปัญหาเดิม:** ตอนเปิด Print Preview แล้วกด Ctrl+P → Save as PDF ของเบราว์เซอร์ ชื่อไฟล์ที่เบราว์เซอร์เสนอจะดึงจาก `<title>` ของหน้า ซึ่งเดิมดึงมาจากชื่อลูกค้า/ผู้ขาย (field `customer_name` / `supplier_name`) ไม่ใช่เลขที่เอกสาร

**สาเหตุเชิงเทคนิค:** `<title>` ของหน้า print มาจาก `doc.get_title()` ซึ่งอ้างตาม `title_field` ของ DocType meta แต่ถ้า `title_field` ถูกเคลียร์เป็นค่าว่างเฉยๆ ระบบจะ fallback ไปใช้ field ที่ชื่อ `title` (เป็น hidden field ของแต่ละ doctype ที่ถูก sync ค่าชื่อลูกค้า/ผู้ขายไว้อีกที) แทนการ fallback ไปที่ `name` — จึงต้องตั้ง `title_field = "name"` ตรงๆ เท่านั้นจึงจะได้เลขที่เอกสารจริง

**วิธีแก้:** สร้าง **Property Setter** (`doctype_or_field = DocType`, `property = title_field`, `value = name`) ให้กับ DocType ต่อไปนี้ ผ่าน API (ไม่แก้ DocType core ตรงๆ เพื่อให้รอดจาก `bench migrate`):

- Sales Invoice
- Quotation
- Sales Order
- Delivery Note
- Purchase Invoice
- Purchase Order
- Purchase Receipt

หลังสร้าง Property Setter แล้วเคลียร์ cache ผ่าน `/api/method/frappe.sessions.clear`

**ผลตรวจสอบจริง (ผ่าน `/printview` endpoint):**

| DocType | ก่อน | หลัง |
|---|---|---|
| Sales Invoice | ชื่อลูกค้า (เช่น "บริษัท อนาวินทร์ กรุ๊ป...") | เลขที่เอกสาร (เช่น `ACC-SINV-2025-00001`) ✅ |
| Quotation | ชื่อลูกค้า | เลขที่เอกสาร ✅ |
| Sales Order | — | เลขที่เอกสาร ✅ |
| Purchase Invoice / Purchase Order / Purchase Receipt / Delivery Note | — | ตั้งค่าเดียวกันแล้ว แต่ตรวจสอบจริงไม่ได้ เพราะ API key ที่ใช้ทดสอบไม่มีสิทธิ์อ่านเอกสารกลุ่มนี้ (เจอ `403 Not Permitted` ซึ่งเป็นสิทธิ์เดิมของ API user ไม่เกี่ยวกับการแก้ครั้งนี้) |

**ผลกระทบที่ผู้ใช้รับทราบและยอมรับแล้ว:** browser tab title / breadcrumb ตอนเปิดฟอร์มเอกสารทั้ง 7 ประเภทนี้จะเปลี่ยนจากแสดง "ชื่อลูกค้า/ผู้ขาย" เป็น "เลขที่เอกสาร" ไปด้วย (เพราะใช้ mechanism เดียวกัน)
