#!/usr/bin/env python3
"""Update headers for all 6 print formats to match Receipt-Test layout."""
import json, os, subprocess

api_key    = os.environ['ERPNEXT_API_KEY']
api_secret = os.environ['ERPNEXT_API_SECRET']
base_url   = os.environ['ERPNEXT_BASE_URL'].rstrip('/').removesuffix('/desk')
auth       = f"Authorization: token {api_key}:{api_secret}"

# ── shared company left block ─────────────────────────────────────────────────
COMPANY_LEFT = """
<table class="info-table" style="margin-bottom:0;">
  <tr>
    <td style="width:55%; vertical-align:middle;">
      <table style="border:none; margin:0;">
        <tr>
          <td style="border:none; padding:0; vertical-align:middle;">
            <img src="/files/Chiangrai-NextStep-logo.png" alt="Logo"
                 style="width:80px; height:auto; display:block;">
          </td>
          <td style="border:none; padding:0 0 0 10px; vertical-align:middle;">
            {% set comp = frappe.get_doc("Address", doc.company_address) %}
            <div style="font-weight:bold; font-size:14px; white-space:nowrap;">{{ comp.address_title }}</div>
            <div style="font-size:12px; color:#444; line-height:1.6;">
              {{ comp.address_line1 }}{% if comp.address_line2 %}, {{ comp.address_line2 }}{% endif %}<br>
              อ.{{ comp.city or '' }}, จ.{{ comp.state or '' }} {{ comp.pincode or '' }}<br>
              Tel: {{ comp.phone or '-' }}
            </div>
          </td>
        </tr>
      </table>
    </td>"""

# ── shared customer address footer ────────────────────────────────────────────
CUSTOMER_FOOTER = """

<hr class="divider" style="margin:6px 0;">

<div style="font-size:14px; margin-bottom:4px;">
  <strong>ชื่อลูกค้า :</strong> {{ doc.customer_name }}
  {% if doc.customer_address %}
  {% set addr = frappe.get_doc("Address", doc.customer_address) %}
  &nbsp;{{ addr.address_line1 }}{% if addr.address_line2 %}, {{ addr.address_line2 }}{% endif %}
  &nbsp;อ.{{ addr.city or '' }}, จ.{{ addr.state or '' }} {{ addr.pincode or '' }}
  {% endif %}
</div>
<hr class="divider" style="margin:4px 0 0 0;">"""

# ── right side: uses doc.name / doc.posting_date ──────────────────────────────
def right_doc(title, font_size=26):
    return (
        "\n\n    <!-- ขวา: Title + เลขที่ + วันที่ -->\n"
        '    <td style="width:45%; text-align:right; vertical-align:middle;">\n'
        '      <div style="font-size:' + str(font_size) + 'px; font-weight:bold;'
        ' letter-spacing:1px; white-space:nowrap;">' + title + '</div>\n'
        '      <div style="font-size:14px;"><strong>เลขที่ :</strong> {{ doc.name }}</div>\n'
        '      <div style="font-size:14px;"><strong>วันที่&nbsp;:</strong>'
        ' {{ frappe.utils.formatdate(doc.posting_date, "d/M/yyyy") }}</div>\n'
        '    </td>\n'
        '  </tr>\n'
        '</table>'
    )

# ── right side: pulls เลขที่/วันที่ from Payment Entry ────────────────────────
RIGHT_PAYMENT = """

    <!-- ขวา: Title + เลขที่ + วันที่ จาก Payment Entry -->
    <td style="width:45%; text-align:right; vertical-align:middle;">
      <div style="font-size:26px; font-weight:bold; letter-spacing:1px; white-space:nowrap;">ใบเสร็จรับเงิน</div>
      {% set rows = frappe.db.sql(\"""
        select pe.name, pe.posting_date
        from `tabPayment Entry` pe
        join `tabPayment Entry Reference` per on per.parent = pe.name
        where per.reference_name = %s
          and pe.docstatus = 1
        order by pe.posting_date desc, pe.modified desc
      \""", (doc.name,), as_dict=1) %}
      {% for r in rows %}
      <div style="font-size:14px;"><strong>เลขที่ :</strong> {{ r.name }}</div>
      <div style="font-size:14px;"><strong>วันที่&nbsp;:</strong> {{ frappe.utils.formatdate(r.posting_date, "d/M/yyyy") }}</div>
      {% endfor %}
    </td>
  </tr>
</table>"""

FORMATS = {
    'CN-SaleInvoice-NoVat':          COMPANY_LEFT + right_doc('ใบส่งสินค้า / ใบแจ้งหนี้') + CUSTOMER_FOOTER,
    'CN-SaleInvoice-Receipt-NoVat':  COMPANY_LEFT + right_doc('ใบส่งสินค้า / ใบเสร็จรับเงิน', 22) + CUSTOMER_FOOTER,
    'CN-SaleInvoice-with-signature': COMPANY_LEFT + right_doc('ใบส่งสินค้า / ใบแจ้งหนี้') + CUSTOMER_FOOTER,
    'CN-SaleInvoice':                COMPANY_LEFT + right_doc('ใบส่งสินค้า / ใบแจ้งหนี้') + CUSTOMER_FOOTER,
    'Receipt-02':                    COMPANY_LEFT + RIGHT_PAYMENT + CUSTOMER_FOOTER,
    'Receipt-Payment-Entry':         COMPANY_LEFT + RIGHT_PAYMENT + CUSTOMER_FOOTER,
}


def fetch(name):
    url = f"{base_url}/api/resource/Print%20Format/{name}"
    r = subprocess.run(['curl', '-s', '-H', auth, url], capture_output=True, text=True)
    return json.loads(r.stdout)


def push(name, data):
    payload = json.dumps({'data': data}, ensure_ascii=False)
    url = f"{base_url}/api/resource/Print%20Format/{name}"
    r = subprocess.run(
        ['curl', '-s', '-X', 'PUT', '-H', auth,
         '-H', 'Content-Type: application/json',
         '--data-raw', payload, url],
        capture_output=True, text=True
    )
    resp = json.loads(r.stdout)
    if 'data' in resp:
        print(f"  OK   {name}  modified={resp['data'].get('modified','?')}")
    else:
        print(f"  ERR  {name}: {r.stdout[:400]}")
    return resp


for fmt_name, new_header in FORMATS.items():
    print(f"\n--- {fmt_name} ---")
    remote = fetch(fmt_name)
    if 'data' not in remote:
        print(f"  fetch failed: {str(remote)[:300]}")
        continue
    data = remote['data']
    fd = json.loads(data['format_data'])
    fd[0]['options'] = new_header
    data['format_data'] = json.dumps(fd, ensure_ascii=False)
    push(fmt_name, data)

print("\nAll done.")
