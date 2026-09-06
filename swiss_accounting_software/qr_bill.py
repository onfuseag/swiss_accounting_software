from decimal import Decimal, ROUND_HALF_UP
import re

import frappe
from frappe import _
from chqr import Creditor, QRBill, UltimateDebtor, ValidationError as QRValidationError

QR_BILL_WIDTH_MM = 210
QR_BILL_HEIGHT_MM = 108
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
TEXT_SCALE = 0.9
MOD10_TABLE = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
VALID_REFERENCE_TYPES = ("QRR", "SCOR", "NON")


def mod10_recursive(value: str) -> str:
	table = MOD10_TABLE
	carry = 0
	for digit in value.replace(" ", ""):
		carry = table[(carry + int(digit)) % 10]
	return str((10 - carry) % 10)


def get_qr_code_type(company: str | None) -> str:
	if not company or not frappe.db.exists("Swiss QR Bill Settings", company):
		return "QRR"
	value = frappe.db.get_value("Swiss QR Bill Settings", company, "qr_code_type")
	if value in VALID_REFERENCE_TYPES:
		return value
	return "QRR"


QRR_BODY_LENGTH = 26
SCOR_PAYLOAD_LENGTH = 21


def invoice_number_part(docname: str, length: int) -> str:
	digits = re.sub(r"\D", "", docname) or "0"
	if len(digits) > length:
		digits = digits[-length:]
	return digits.zfill(length)


def get_qr_reference(docname: str) -> str:
	body = invoice_number_part(docname, QRR_BODY_LENGTH)
	return f"{body}{mod10_recursive(body)}"


def iso11649_check_digits(payload: str) -> str:
	rearranged = f"{payload}RF00"
	numeric = ""
	for char in rearranged.upper():
		if char.isdigit():
			numeric += char
		else:
			numeric += str(ord(char) - ord("A") + 10)
	return f"{98 - (int(numeric) % 97):02d}"


def get_scor_reference(docname: str) -> str:
	payload = invoice_number_part(docname, SCOR_PAYLOAD_LENGTH)
	return f"RF{iso11649_check_digits(payload)}{payload}"


def get_payment_reference(invoice, reference_type: str | None = None) -> str | None:
	if reference_type is None:
		reference_type = get_qr_code_type(invoice.company)
	if reference_type == "NON":
		return None

	existing = (invoice.get("esr_reference_code") or "").replace(" ", "")
	if reference_type == "SCOR":
		if existing.upper().startswith("RF") and 5 <= len(existing) <= 25:
			return existing.upper()
		return get_scor_reference(invoice.name)

	if existing.isdigit() and len(existing) == 27:
		return existing
	return get_qr_reference(invoice.name)


def get_qr_language(language: str | None) -> str:
	if not language:
		return "de"

	lang = language.lower()
	if lang.startswith("en"):
		return "en"
	if lang.startswith("fr"):
		return "fr"
	if lang.startswith("it"):
		return "it"
	if lang.startswith("de"):
		return "de"
	return "de"


def generate_qr_slip_pdfs(invoice) -> list[bytes]:
	language = get_qr_language(invoice.language)
	return [
		svg_to_pdf(build_qr_bill(invoice, **entry).generate_svg(language=language))
		for entry in get_qr_bill_entries(invoice)
	]


def generate_qr_slip_pdf(invoice) -> bytes:
	return generate_qr_slip_pdfs(invoice)[0]


def get_qr_bill_entries(invoice) -> list[dict]:
	if should_create_qr_per_payment_term(invoice):
		rows = [row for row in invoice.payment_schedule if _term_amount(row) > 0]
		if rows:
			total = len(rows)
			return [
				{
					"amount": _term_amount(row),
					"additional_information": payment_term_message(row, idx, total),
				}
				for idx, row in enumerate(rows, start=1)
			]

	return [
		{
			"amount": Decimal(str(invoice.outstanding_amount or 0)).quantize(
				Decimal("0.01"), rounding=ROUND_HALF_UP
			),
			"additional_information": None,
		}
	]


def should_create_qr_per_payment_term(invoice) -> bool:
	if not invoice.company or not frappe.db.exists("Swiss QR Bill Settings", invoice.company):
		return False
	if not frappe.db.get_value("Swiss QR Bill Settings", invoice.company, "qr_bill_per_invoice"):
		return False
	return bool(invoice.get("payment_schedule"))


def _term_amount(row) -> Decimal:
	return Decimal(str(row.outstanding or row.payment_amount or 0)).quantize(
		Decimal("0.01"), rounding=ROUND_HALF_UP
	)


def payment_term_message(row, idx: int, total: int) -> str:
	parts = [f"{idx}/{total}"]
	if row.payment_term:
		parts.append(str(row.payment_term))
	elif row.description:
		parts.append(str(row.description).strip())
	if row.due_date:
		parts.append(str(row.due_date))
	return clip(" - ".join(parts), 140) or ""


def build_qr_bill(
	invoice,
	amount: Decimal | None = None,
	additional_information: str | None = None,
) -> QRBill:
	if invoice.currency not in ("CHF", "EUR"):
		frappe.throw(_("Currency should be either CHF or EUR"))

	if not frappe.db.exists("Swiss QR Bill Settings", invoice.company):
		frappe.throw(_("Please create Swiss QR Bill Settings for {0}").format(invoice.company))

	settings = frappe.get_doc("Swiss QR Bill Settings", invoice.company)
	if not settings.bank_account:
		frappe.throw(_("Bank Account is missing in Swiss QR Bill Settings for {0}").format(invoice.company))

	iban = frappe.db.get_value("Bank Account", settings.bank_account, "iban")
	if not iban:
		frappe.throw(_("IBAN is missing on Bank Account {0}").format(settings.bank_account))
	iban = iban.replace(" ", "")

	company_address = get_address_doc(invoice.company_address, _("Company Address"))
	customer_address = get_address_doc(invoice.customer_address, _("Customer Address"))
	customer_name = invoice.customer_name or invoice.customer
	if not customer_name:
		frappe.throw(_("Customer is required for QR-bill generation"))

	if amount is None:
		amount = Decimal(str(invoice.outstanding_amount or 0)).quantize(
			Decimal("0.01"), rounding=ROUND_HALF_UP
		)

	reference_type = settings.qr_code_type if settings.qr_code_type in VALID_REFERENCE_TYPES else "QRR"
	reference = get_payment_reference(invoice, reference_type)

	try:
		return QRBill(
			account=iban,
			creditor=build_party(invoice.company, company_address, Creditor),
			debtor=build_party(customer_name, customer_address, UltimateDebtor),
			amount=amount,
			currency=invoice.currency,
			reference_type=reference_type,
			reference=reference,
			additional_information=additional_information or None,
		)
	except QRValidationError as e:
		frappe.throw(_("QR-bill validation failed: {0}").format(str(e)))


def build_party(name: str, address, party_class):
	return party_class(
		name=clip(name, 70) or "",
		street=clip(address.address_line1, 70),
		building_number=clip(address.address_line2, 16),
		postal_code=clip(address.pincode, 16) or "",
		city=clip(address.city, 35) or "",
		country=get_country_code(address.country),
	)


def get_address_doc(address_name: str | None, label: str):
	if not address_name:
		frappe.throw(_("{0} is required for QR-bill generation").format(label))
	return frappe.get_doc("Address", address_name)


def get_country_code(country_name: str | None) -> str:
	if not country_name:
		frappe.throw(_("Country is required for QR-bill generation"))

	code = frappe.db.get_value("Country", country_name, "code")
	if not code:
		frappe.throw(_("Could not find ISO country code for {0}").format(country_name))
	return code.upper()


def clip(value, length: int) -> str | None:
	if value is None:
		return None
	text = str(value).strip()
	if not text:
		return None
	return text[:length]


def scale_svg_fonts(svg_content: str, scale: float) -> str:
	def replace_font_size(match):
		value = float(match.group(1))
		unit = match.group(2)
		return f'font-size="{value * scale:.2f}{unit}"'

	return re.sub(r'font-size="([\d.]+)(pt|px|mm)"', replace_font_size, svg_content)


def svg_to_pdf(svg_content: str) -> bytes:
	import frappe.utils.pdf  # apply Frappe's pdfkit patches
	import pdfkit

	svg = svg_content.lstrip()
	if svg.startswith("<?xml"):
		svg = svg.split("?>", 1)[-1]
	svg = svg.lstrip()
	svg = scale_svg_fonts(svg, TEXT_SCALE)
	svg = re.sub(r"^<svg\b", f'<svg x="0mm" y="{A4_HEIGHT_MM - QR_BILL_HEIGHT_MM}mm"', svg, count=1)

	html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
	html, body {{
		margin: 0;
		padding: 0;
		width: {A4_WIDTH_MM}mm;
		height: {A4_HEIGHT_MM}mm;
		overflow: hidden;
		background: #fff;
	}}
	body > svg {{
		display: block;
		width: {A4_WIDTH_MM}mm;
		height: {A4_HEIGHT_MM}mm;
	}}
</style>
</head>
<body>
	<svg width="{A4_WIDTH_MM}mm" height="{A4_HEIGHT_MM}mm" xmlns="http://www.w3.org/2000/svg">
		<rect x="0mm" y="0mm" width="{A4_WIDTH_MM}mm" height="{A4_HEIGHT_MM}mm" fill="#ffffff"/>
		{svg}
	</svg>
</body>
</html>"""

	options = {
		"page-width": f"{A4_WIDTH_MM}mm",
		"page-height": f"{A4_HEIGHT_MM}mm",
		"margin-top": "0",
		"margin-bottom": "0",
		"margin-left": "0",
		"margin-right": "0",
		"disable-smart-shrinking": "",
		"encoding": "UTF-8",
		"print-media-type": "",
	}
	pdf = pdfkit.from_string(html, False, options=options)
	if not pdf:
		frappe.throw(_("Failed to convert QR-bill SVG to PDF"))
	if isinstance(pdf, str):
		pdf = pdf.encode("latin-1")
	return pdf
