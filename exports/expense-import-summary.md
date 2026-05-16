# Expense Import Summary

## Scope

เอกสารนี้สรุปงานแปลงข้อมูลค่าใช้จ่ายจากไฟล์ Excel ภายนอกให้อยู่ในรูปแบบที่นำเข้า ERPNext ได้, การปรับ mapping บัญชี, การ import ผ่าน API, การ submit เอกสาร, และการตรวจสอบยอดหลังลงบัญชี

วันที่ดำเนินการ: 2026-05-12  
ระบบ: ERPNext / Company `Chiangrai Nextstep`

## Source Files

- ไฟล์ต้นทาง: `exports/expens.xlsx`
- ชีตต้นทาง:
  - `2568`
  - `2569`

โครงสร้างไฟล์ต้นทางเป็นแบบหลายบรรทัดต่อ 1 เอกสาร:

- แถวแรกของเอกสารมี `วันที่`, `เลขที่เอกสาร`, `ผู้รับเงิน`
- แถวถัดไปเป็นรายการย่อย โดยคอลัมน์หลักว่าง
- จึงไม่สามารถนำเข้า ERPNext ได้โดยตรง

## Transformation Flow

### 1. Normalize Source Data

สร้างไฟล์:

- `exports/expens-normalized.xlsx`

สิ่งที่ทำ:

- ตัดแถว `รวม` ออก
- fill-down ค่า `วันที่`, `เลขที่เอกสาร`, `ผู้รับเงิน`
- แยกเป็น 1 บรรทัดต่อ 1 รายการ
- เพิ่ม `Line No`
- เพิ่ม `Document Total`

ผลลัพธ์:

- เอกสาร 71 ใบ
- รายการรวม 306 บรรทัด

### 2. Build Journal Entry Import Files

สร้างไฟล์หลายรุ่นระหว่างปรับ mapping:

- `exports/expens-journal-entry-import.xlsx`
- `exports/expens-journal-entry-import.csv`
- `exports/expens-journal-entry-import-v2.xlsx`
- `exports/expens-journal-entry-import-v2.csv`
- `exports/expens-journal-entry-import-v3.xlsx`
- `exports/expens-journal-entry-import-v3.csv`
- ไฟล์ final:
  - `exports/expens-journal-entry-import-final.xlsx`
  - `exports/expens-journal-entry-import-final.csv`

รูปแบบที่ใช้:

- `DocType`: `Journal Entry`
- นำเข้าแบบ parent-child
- ใช้ `Draft` ก่อน แล้ว submit ภายหลัง

## ERPNext Defaults Used

- Company: `Chiangrai Nextstep`
- Voucher Type: `Journal Entry`
- Naming Series: `ACC-JV-.YYYY.-`
- Default Cost Center: `Main - CN`
- Default Credit Account: `1110 - Cash - CN`

## Final Mapping Decisions

### Administrative Expenses

ลงบัญชี `5201 - Administrative Expenses - CN`

กลุ่มรายการ:

- `ค่าภาษีสุรา`
- `มหาดไทยสุรา`
- `ค่าใช้จ่ายสุรา`
- `เงินบำรุง สสส.`
- `เงินบำรุองค์การฯสุรา`
- `เงินฝากบำรุองค์การฯสุรา`
- `เงินบำรุง กกท.`
- `เงินบำรุงกองทุนเพื่อผู้สูงอายุ`
- `ค่าบำรุงสมาชิกสภาอุตสาหกรรมฯ ปี 2568`
- `ค่าบำรุงสมาชิกสถาบันรหัสสากล EAN13 ปี 2568`
- `แผ่นชั้นไม้เมลามีน`

### Cost of Goods Sold

ลงบัญชี `5111 - Cost of Goods Sold - CN`

กลุ่มรายการ:

- วัตถุดิบการผลิต
- น้ำตาล
- ยีสต์
- สมุนไพร
- ขวด
- ฝา
- จุก
- กล่อง
- สติ๊กเกอร์
- ฉลาก
- ค่าจ้าง/ค่ากระดาษที่เป็นส่วนของบรรจุภัณฑ์
- `CWD-0023: 22.5x34: BK02: A00 22.5mm`
  - ผู้ใช้ยืนยันว่าเป็น `ขวดเหล้า`
- `แก๊ส LPG 48 กิโล`
- `แก๊ส LPG 15 กิโล`
  - ผู้ใช้ยืนยันว่าเป็นเชื้อเพลิงในการกลั่น
- รายการล้างขวด:
  - `น้ำยาล้างจาน ...`
  - `แผ่นใยขัด ...`
  - ผู้ใช้ยืนยันให้ลง `5111`

### Freight and Forwarding Charges

ลงบัญชี `5205 - Freight and Forwarding Charges - CN`

กลุ่มรายการ:

- `ค่าขนส่ง-ต้นทาง`
- `ค่าส่ง`
- `รายได้ค่าจัดส่ง`
- `รายได้จากการจัดส่ง`

หมายเหตุ:

- เดิมมีความเสี่ยงว่าจะตัดรายการ `รายได้...` ออกจาก import
- ผู้ใช้ยืนยันว่า `ไม่ตัด` และให้ลงบัญชีให้ถูก
- จึงคงรายการเหล่านี้ไว้และลงเป็นค่าขนส่ง

### Office Maintenance Expenses

ลงบัญชี `5208 - Office Maintenance Expenses - CN`

กลุ่มรายการ:

- วัสดุซ่อมบำรุง
- อุปกรณ์ช่าง
- อุปกรณ์ทำความสะอาดบางส่วน
- ฮาร์ดแวร์อาคาร
- `ชุดทดสอบสารหนู`
  - ผู้ใช้ยืนยันให้ลง `5208`

### Utility Expenses

ลงบัญชี `5217 - Utility Expenses - CN`

กลุ่มรายการ:

- `แก๊สโซฮอล์ 95`
- `แก็สกระป๋อง`
- รายการสาธารณูปโภคทั่วไปถ้ามี

### Print and Stationery

ลงบัญชี `5211 - Print and Stationery - CN`

กลุ่มรายการ:

- `หมึกพิมพ์ ...`
- `กระดาษอาร์ต ...`

### Miscellaneous Expenses

ลงบัญชี `5221 - Miscellaneous Expenses - CN`

ใช้เฉพาะรายการ fallback ที่ยังไม่เข้าเงื่อนไขข้างต้น

## Special Clarifications from User

### `CWD-0023: 22.5x34...`

ผู้ใช้ยืนยัน:

- เป็น `ขวดเหล้า`

ผลลัพธ์:

- ลง `5111 - Cost of Goods Sold - CN`

### `แก๊ส LPG 48/15 กิโล`

ผู้ใช้ยืนยัน:

- เป็นค่าเชื้อเพลิงในการกลั่น

ผลลัพธ์:

- ลง `5111 - Cost of Goods Sold - CN`

### เอกสาร `C05020369/0002628`

พบว่าภายในเอกสารมีรายการปนหลายประเภท:

- ภาษีสุรา
- ขวด/ฝา
- ประตู/หน้าต่าง
- สติ๊กเกอร์
- แก๊ส LPG
- รายการจัดส่ง

ผู้ใช้ยืนยัน:

- ไม่ต้องตัดออก
- ให้ลงบัญชีตามรายการจริง

ผลลัพธ์:

- ภาษี -> `5201`
- ขวด/ฝา/สติ๊กเกอร์ -> `5111`
- อุปกรณ์ซ่อมบำรุง/ประตู/หน้าต่าง -> `5208`
- LPG -> `5111`
- ค่าจัดส่ง -> `5205`

## Final Import Files

ใช้ไฟล์ final:

- `exports/expens-journal-entry-import-final.xlsx`
- `exports/expens-journal-entry-import-final.csv`

## API Import Execution

### Draft Creation

นำเข้าเป็น Draft ผ่าน ERPNext API โดยสร้าง `Journal Entry` ทีละใบ

ผลลัพธ์:

- สร้างสำเร็จ 71 ใบ
- Error 0

ไฟล์อ้างอิง:

- `exports/expens-journal-entry-import-manifest.json`

### Submit

ตอน submit รอบแรกพบปัญหา:

- `TimestampMismatchError`

สาเหตุ:

- ส่ง submit ด้วย document stub ทำให้ timestamp ในระบบเปลี่ยนก่อน submit

วิธีแก้:

- ดึงเอกสารล่าสุดจาก ERPNext ก่อน
- submit ด้วย document ล่าสุดจาก API

ผลลัพธ์:

- submit สำเร็จ 71 ใบ
- Error 0

ไฟล์อ้างอิง:

- `exports/expens-journal-entry-submit-manifest.json`

## Verification

ตรวจยอดทั้งจากไฟล์ final และจาก ERPNext จริงหลัง submit

ผลตรวจ:

- จำนวนเอกสาร: 71
- สถานะใน ERPNext: `Submitted` 71 ใบ
- ยอดรวม Debit: `346,272.13`
- ยอดรวม Credit: `346,272.13`

ยอดตรงกันครบ

ไฟล์อ้างอิง:

- `exports/expens-journal-entry-verification.json`

## Rollback Procedure

### กรณีเอกสารยังเป็น Draft

1. ไปที่รายการ `Journal Entry`
2. filter ด้วย `user_remark contains API import from expens-journal-entry-import-final`
3. ลบเอกสารชุดนี้ได้เลย

### กรณีเอกสารถูก Submit แล้ว

1. filter เอกสารชุดเดียวกัน
2. `Cancel` ก่อน
3. ถ้าต้องเอาออกจากระบบจริงค่อย `Delete` หลังจากเป็น Cancelled

### ใช้ Manifest ช่วย Rollback

ใช้ไฟล์:

- `exports/expens-journal-entry-import-manifest.json`
- `exports/expens-journal-entry-submit-manifest.json`

เพื่อระบุรายชื่อเอกสารจริงใน ERPNext เช่น `ACC-JV-2026-00001`

## Final Outcome

งานเสร็จสมบูรณ์ดังนี้:

- แปลงไฟล์ค่าใช้จ่ายจาก Excel ภายนอกเป็นรูปแบบ import ได้
- ปรับ mapping บัญชีตามข้อมูลจริงและคำยืนยันจากผู้ใช้
- import เข้า ERPNext ผ่าน API สำเร็จ
- submit เอกสารสำเร็จ
- ตรวจสอบยอดสำเร็จและ balance ถูกต้อง

## Generated Artifacts

- `exports/expens.xlsx`
- `exports/expens-normalized.xlsx`
- `exports/expens-journal-entry-import-final.xlsx`
- `exports/expens-journal-entry-import-final.csv`
- `exports/expens-journal-entry-import-manifest.json`
- `exports/expens-journal-entry-submit-manifest.json`
- `exports/expens-journal-entry-verification.json`
- `exports/expense-import-summary.md`
