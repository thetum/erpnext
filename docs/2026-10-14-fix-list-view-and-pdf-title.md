# สรุปงาน ERPNext — 2026-10-14

ระบบ: `https://erp.chiangrai-nextstep.com` (Frappe 16.34.0 / ERPNext 16.35.0)
แก้ผ่าน REST API และตรวจผลจริงผ่านเบราว์เซอร์ (Playwright)

แก้ต่อจาก [2026-10-12-erpnext-items-and-pdf-filename.md](2026-10-12-erpnext-items-and-pdf-filename.md) ข้อ 2

## 1. หน้า list ไม่แสดงข้อมูล (`/desk/sales-invoice` ฯลฯ)

**อาการ:** หน้า list ของ Sales Invoice ว่างเปล่า ทั้งที่มีเอกสาร 134 ใบ และ API `frappe.desk.reportview.get` ตอบข้อมูลปกติ

**สาเหตุ:** Property Setter `title_field = "name"` ที่สร้างเมื่อ 2026-10-12 ใน list view ของ Frappe v16 คอลัมน์แรกถูกสร้างจาก `frappe.meta.get_docfield(doctype, title_field)` แต่ `name` ไม่ใช่ docfield จริง ค่า `df` จึงเป็น `undefined` แล้ว JS พังก่อนวาดตาราง:

```text
TypeError: Cannot read properties of undefined (reading 'fieldname')
    at frappe.views.ListView.get_header_html (list.bundle.js)
    at frappe.views.ListView.render_header
    at frappe.views.ListView.setup_view
```

ปัญหานี้เกิดกับ list ของทั้ง 7 DocType ที่ตั้งค่านี้

**การแก้:** ลบ Property Setter ทั้ง 7 ตัว ระบบจะ clear cache ของ DocType ให้อัตโนมัติเมื่อลบ

- `Sales Invoice-main-title_field`
- `Quotation-main-title_field`
- `Sales Order-main-title_field`
- `Delivery Note-main-title_field`
- `Purchase Invoice-main-title_field`
- `Purchase Order-main-title_field`
- `Purchase Receipt-main-title_field`

**ผลตรวจสอบ:** list ทั้ง 7 หน้าแสดงข้อมูลได้ ไม่มี JS error และ `title_field` กลับเป็น `customer_name` / `supplier_name` ตามเดิม

> ห้ามตั้ง `title_field` เป็น `name` อีก ถ้าจำเป็นต้องเปลี่ยน ให้ชี้ไปที่ field ที่มีอยู่จริงใน DocType เท่านั้น

## 2. ชื่อไฟล์ PDF เป็นเลขที่เอกสาร (ทำใหม่ที่ Print Format)

เมื่อลบ Property Setter แล้ว `<title>` ของหน้า `/printview` (หน้าที่เปิดเมื่อกด Print) กลับไปเป็นชื่อลูกค้า จึงเปลี่ยนไปตั้ง title ใน Print Format แทน

**Print Format ที่แก้:**

- `CN-SaleInvoice-with-signature` (default ของ Sales Invoice)
- `Receipt-02`

ทั้งสอง format สร้างด้วย Print Format Builder เพิ่มโค้ดต่อไปนี้ท้ายบล็อก HTML ส่วน `<!-- SECTION: FOOTER -->` (`format_data[6]`):

```html
<!-- PDF-FILENAME: use document number as page title -->
<script>document.title = {{ doc.name | tojson }};</script>
```

**ผลตรวจสอบ** (`ACC-SINV-2026-00088`):

| Print Format | title หลังโหลด `/printview` | `download_pdf` |
|---|---|---|
| CN-SaleInvoice-with-signature | `ACC-SINV-2026-00088` ✅ | 200, `filename=ACC-SINV-2026-00088.pdf` |
| Receipt-02 | `ACC-SINV-2026-00088` ✅ | 200, `filename=ACC-SINV-2026-00088.pdf` |

**ข้อจำกัด:**

- `<title>` ที่เซิร์ฟเวอร์ส่งมายังเป็นชื่อลูกค้า โค้ด JS จะเปลี่ยนเป็นเลขที่เอกสารหลังหน้าโหลดเสร็จ ซึ่งทันก่อนกด Print / Save as PDF
- Print Format อื่น (เช่น Quotation, Sales Order) ยังได้ชื่อลูกค้าเป็นชื่อไฟล์ ถ้าต้องการให้เพิ่มโค้ดเดียวกันใน format นั้น
- ถ้าแก้ format ใน Print Format Builder ระวังอย่าลบบล็อกนี้

## Rollback

- **Property Setter:** สร้างใหม่ได้จากค่าเดิม (`doctype_or_field = DocType`, `property = title_field`, `value = name`) แต่จะทำให้ list view พังอีก จึงไม่แนะนำ
- **Print Format:** ลบ 2 บรรทัดข้างบนออกจากบล็อก FOOTER ของแต่ละ format
