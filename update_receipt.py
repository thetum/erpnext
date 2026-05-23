import json

with open('/mnt/d/Job/erp-next/reports/Receipt-Test.json') as f:
    data = json.load(f)

# ===== CSS =====
data['data']['css'] = """
  * { font-family: 'Sarabun', 'TH Sarabun New', sans-serif; }

  .text-center { text-align: center; }
  .text-right  { text-align: right; }
  .text-left   { text-align: left; }

  div.print-heading, .print-heading {
    display: none !important; visibility: hidden;
    height: 0; line-height: 0; font-size: 0;
  }

  hr.divider { border: none; border-top: 0.5px solid #bbb; margin: 6px 0; }

  table.info-table { width: 100%; border-collapse: collapse; }
  table.info-table td { border: none; padding: 1px 0; vertical-align: top; }

  table.detail-table { width: 100%; border-collapse: collapse; margin-top: 0; }

  table.detail-table thead th {
    background-color: #f0f0f0;
    color: #222;
    padding: 6px 8px;
    border: 0.5px solid #999;
    text-align: center;
    font-size: 13px;
    font-weight: bold;
  }

  table.detail-table tbody td {
    border: 0.5px solid #bbb;
    padding: 5px 8px;
    font-size: 14px;
  }

  table.detail-table tbody tr:nth-child(even) td {
    background-color: #fafafa;
  }

  table.detail-table .total-row .empty-cell {
    background-color: #fff;
    border: none;
  }

  table.detail-table .total-row .total-label,
  table.detail-table .total-row .total-value {
    background-color: #f0f0f0;
    color: #111;
    border: 0.5px solid #999;
    padding: 7px 10px;
    font-size: 15px;
    font-weight: bold;
  }

  table.borderless { border-collapse: collapse; width: 100%; }
  table.borderless th, table.borderless td { border: none; padding: 4px; }

  .sig-box { border: 0.5px solid #666; text-align: center; }
  .sig-box .sig-label {
    border-bottom: 0.5px solid #666; padding: 5px;
    background-color: #f0f0f0; font-weight: bold; font-size: 13px;
  }
  .sig-box .sig-area {
    height: 65px; display: flex;
    align-items: center; justify-content: center;
  }
  .sig-box .sig-name {
    border-top: 0.5px solid #666; padding: 5px;
    min-height: 28px; font-size: 13px;
  }
"""

fd = json.loads(data['data']['format_data'])

# ===== BLOCK 0: Header =====
header_sql = '{% set rows = frappe.db.sql("""' + """
        select pe.name, pe.posting_date
        from `tabPayment Entry` pe
        join `tabPayment Entry Reference` per on per.parent = pe.name
        where per.reference_name = %s
          and pe.docstatus = 1
        order by pe.posting_date desc, pe.modified desc
      """ + '""", (doc.name,), as_dict=1) %}'

fd[0]['options'] = """
<table class="info-table" style="margin-bottom:0;">
  <tr>
    <td style="width:50%; vertical-align:middle;">
      <table style="border:none; margin:0;">
        <tr>
          <td style="border:none; padding:0; width:46px; vertical-align:middle;">
            <img src="/files/Chiangrai-NextStep-logo.png" alt="Logo" style="width:42px; height:auto;">
          </td>
          <td style="border:none; padding:0 0 0 8px; vertical-align:middle;">
            {{% set comp = frappe.get_doc("Address", doc.company_address) %}}
            <div style="font-weight:bold; font-size:15px;">{{{{ comp.address_title }}}}</div>
            <div style="font-size:12px; color:#555; line-height:1.4;">
              {{{{ comp.address_line1 }}}}{{% if comp.address_line2 %}}, {{{{ comp.address_line2 }}}}{{% endif %}}<br>
              อ.{{{{ comp.city or '' }}}}, จ.{{{{ comp.state or '' }}}} {{{{ comp.pincode or '' }}}}
              &nbsp;Tel: {{{{ comp.phone or '-' }}}}
            </div>
          </td>
        </tr>
      </table>
    </td>
    <td style="width:50%; text-align:right; vertical-align:middle;">
      <div style="font-size:26px; font-weight:bold; letter-spacing:1px;">ใบเสร็จรับเงิน</div>
      """ + header_sql + """
      {{% for r in rows %}}
      <div style="font-size:14px;"><strong>เลขที่ :</strong> {{{{ r.name }}}}</div>
      <div style="font-size:14px;"><strong>วันที่&nbsp; :</strong> {{{{ frappe.utils.formatdate(r.posting_date, "d/M/yyyy") }}}}</div>
      {{% endfor %}}
    </td>
  </tr>
</table>

<hr class="divider" style="margin:6px 0;">

<div style="font-size:14px; margin-bottom:4px;">
  <strong>ชื่อลูกค้า :</strong> {{{{ doc.customer_name }}}}
  {{% if doc.customer_address %}}
  {{% set addr = frappe.get_doc("Address", doc.customer_address) %}}
  &nbsp;{{{{ addr.address_line1 }}}}{{% if addr.address_line2 %}}, {{{{ addr.address_line2 }}}}{{% endif %}}
  &nbsp;อ.{{{{ addr.city or '' }}}}, จ.{{{{ addr.state or '' }}}} {{{{ addr.pincode or '' }}}}
  {{% endif %}}
</div>
<hr class="divider" style="margin:4px 0 0 0;">
""".format()

# ===== BLOCK 3: Detail =====
fd[3]['options'] = """
<!-- SECTION: DETAIL -->
<table class="detail-table">
  <thead>
    <tr>
      <th style="width:5%; text-align:center;">ลำดับ</th>
      <th style="width:45%; text-align:left;">รายการ</th>
      <th style="width:8%; text-align:center;">จำนวน</th>
      <th style="width:7%; text-align:center;">หน่วย</th>
      <th style="width:16%; text-align:right;">ราคาต่อหน่วย</th>
      <th style="width:16%; text-align:right;">ราคารวม</th>
    </tr>
  </thead>
  <tbody>
    {% for item in doc.items %}
    <tr>
      <td class="text-center">{{ loop.index }}</td>
      <td class="text-left">{{ item.item_name }}{% if item.description %} {{ item.description }}{% endif %}</td>
      <td class="text-center">{{ item.qty|int }}</td>
      <td class="text-center">{{ item.uom or '' }}</td>
      <td class="text-right">{{ "{:,.2f}".format(item.rate) }}</td>
      <td class="text-right">{{ "{:,.2f}".format(item.amount) }}</td>
    </tr>
    {% endfor %}
  </tbody>
  <tfoot>
    <tr class="total-row">
      <th colspan="4" class="empty-cell"></th>
      <th class="total-label text-right">รวมทั้งสิ้น</th>
      <th class="total-value text-right">{{ "{:,.2f}".format(doc.grand_total) }}</th>
    </tr>
  </tfoot>
</table>
"""

data['data']['format_data'] = json.dumps(fd, ensure_ascii=False)

with open('/mnt/d/Job/erp-next/reports/Receipt-Test.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open('/mnt/d/Job/erp-next/reports/Receipt-Test/header.html', 'w') as f:
    f.write(fd[0]['options'])
with open('/mnt/d/Job/erp-next/reports/Receipt-Test/detail.html', 'w') as f:
    f.write(fd[3]['options'])
with open('/mnt/d/Job/erp-next/reports/Receipt-Test/css.css', 'w') as f:
    f.write(data['data']['css'])

print("done")
