"""Exercise real QR payloads and SVGs without requiring a Frappe site."""

from datetime import date, datetime
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from chqr.constants import ALLOWED_NOTIFICATION_TEXTS

SOURCE = Path(__file__).resolve().parents[1] / "swiss_accounting_software"
SVG = "{http://www.w3.org/2000/svg}"


def load_source(name):
	# Loading the source directly avoids the app's site-dependent initialization.
	spec = importlib.util.spec_from_file_location(name + "_under_test", SOURCE / (name + ".py"))
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


information_module = load_source("billing_information")
billing_information = information_module.billing_information
fit_message = information_module.fit_message
invoice_message = information_module.invoice_message


class Document(SimpleNamespace):
	def get(self, name):
		return getattr(self, name, None)


class BillingInformationTests(unittest.TestCase):
	def test_invoice_number_and_date_are_structured(self):
		self.assertEqual(
			billing_information("DEMO-2026-00001", "2026-01-15"),
			"//S1/10/DEMO-2026-00001/11/260115",
		)

	def test_reserved_separators_are_escaped(self):
		self.assertEqual(
			billing_information("DEMO/1\\2", date(2026, 1, 15)),
			"//S1/10/DEMO\\/1\\\\2/11/260115",
		)

	def test_swiss_tax_id_formats(self):
		for tax_id in ["CHE-123.456.789", "123456789", "CHE-123.456.789 TVA", "CHE-123.456.789 MWST / TVA / IVA"]:
			with self.subTest(tax_id=tax_id):
				self.assertEqual(
					billing_information("DEMO", "2026-01-15", tax_id),
					"//S1/10/DEMO/11/260115/30/123456789",
				)

	def test_invalid_metadata_is_rejected(self):
		for number, day, tax_id in [
			("", "2026-01-15", None),
			("DEMO\nEPD", "2026-01-15", None),
			("DEMO", "2026-02-30", None),
			("DEMO", "2026-01-15", "DE123456789"),
			("X" * 140, "2026-01-15", None),
		]:
			with self.subTest(number=number, tax_id=tax_id), self.assertRaises(ValueError):
				billing_information(number, day, tax_id)

	def test_combined_limit_preserves_structured_information(self):
		information = billing_information("DEMO", "2026-01-15")
		remaining = 140 - len(information)
		self.assertEqual(fit_message("X" * remaining, information), "X" * remaining)
		message = fit_message("X" * (remaining + 1), information)
		self.assertEqual(len(message) + len(information), 140)
		self.assertTrue(message.endswith("..."))
		self.assertIsNone(fit_message("Text", "X" * 140))

	def test_installment_details_are_preserved_before_description(self):
		information = billing_information("DEMO", "2026-01-15")
		installment = "1/2 - Due 15.02.2026"
		message = fit_message("Long invoice description " * 20, information, installment)
		self.assertTrue(message.startswith(installment))
		self.assertLessEqual(len(message) + len(information), 140)
		self.assertTrue(message.endswith("..."))

	def test_insufficient_space_for_installment_is_rejected(self):
		with self.assertRaisesRegex(ValueError, "(?i)installment"):
			fit_message("Invoice DEMO", "X" * 135, "1/2 - Due 15.02.2026")

	def test_invoice_description_is_english(self):
		for day in [date(2026, 1, 15), datetime(2026, 1, 15), "2026-01-15"]:
			with self.subTest(day=day):
				self.assertEqual(invoice_message("DEMO", day), "Invoice DEMO dated 15.01.2026")


class QRBillIntegrationTests(unittest.TestCase):
	def setUp(self):
		self.per_term = False
		self.tax_id = None
		self.company_lookups = []
		self.address = Document(
			address_line1="Example Street", address_line2="1", pincode="3000",
			city="Bern", country="Switzerland",
		)
		self.settings = Document(
			bank_account="Example Account", qr_code_type="QRR",
			include_tax_id_in_payment_information=0,
		)
		frappe = ModuleType("frappe")
		frappe._ = lambda value: value
		frappe.db = SimpleNamespace(exists=lambda *args: True, get_value=self.get_value)
		frappe.get_doc = lambda kind, name: self.settings if kind == "Swiss QR Bill Settings" else self.address

		def throw(message):
			raise ValueError(message)

		frappe.throw = throw
		spec = importlib.util.spec_from_file_location("qr_bill_under_test", SOURCE / "qr_bill.py")
		self.module = importlib.util.module_from_spec(spec)
		package = ModuleType("swiss_accounting_software")
		package.__path__ = [str(SOURCE)]
		with patch.dict(sys.modules, {"frappe": frappe, "swiss_accounting_software": package}):
			spec.loader.exec_module(self.module)
		self.invoice = Document(
			name="DEMO-2026-00001", posting_date="2026-01-15", language="en",
			company="Example Company", company_address="Company Address",
			customer_address="Customer Address", customer_name="Example Customer",
			customer="CUSTOMER-DEMO", outstanding_amount=Decimal("100.00"), currency="CHF",
			esr_reference_code="210000000003139471430009017", payment_schedule=[],
		)

	def get_value(self, kind, name, field):
		if kind == "Country":
			return "CH"
		if kind == "Bank Account":
			return "CH4431999123000889012" if self.settings.qr_code_type == "QRR" else "CH9300762011623852957"
		if kind == "Company":
			self.company_lookups.append((name, field))
			return self.tax_id
		if field == "qr_bill_per_invoice":
			return self.per_term
		return self.settings.qr_code_type

	def set_installments(self):
		self.per_term = True
		self.invoice.payment_schedule = [
			Document(outstanding=50, payment_amount=50, payment_term="Installment", description=None, due_date=day)
			for day in ["2026-02-15", "2026-03-15"]
		]

	def test_payload_keeps_qrr_amount_and_separate_information_fields(self):
		bill = self.module.build_qr_bill(self.invoice)
		self.assertEqual(bill.build_data_string().split("\n")[27:32], [
			"QRR", "210000000003139471430009017",
			"Invoice DEMO-2026-00001 dated 15.01.2026", "EPD",
			"//S1/10/DEMO-2026-00001/11/260115",
		])
		self.assertEqual(bill.amount, Decimal("100.00"))
		self.assertIsNotNone(bill.generate_qr_code())

	def test_scor_and_non_keep_their_reference_rules(self):
		for kind in ["SCOR", "NON"]:
			with self.subTest(kind=kind):
				self.settings.qr_code_type = kind
				self.invoice.esr_reference_code = None
				expected = self.module.get_payment_reference(self.invoice, kind)
				bill = self.module.build_qr_bill(self.invoice)
				self.assertEqual(bill.reference, expected or "")
				self.assertEqual(bill.reference_type, kind)
				self.assertEqual(bill.amount, Decimal("100.00"))
				self.assertTrue(bill.billing_information.startswith("//S1/10/"))

	def test_tax_id_disabled_ignores_invalid_company_tax_id(self):
		self.tax_id = "DE123456789"
		bill = self.module.build_qr_bill(self.invoice)
		self.assertNotIn("/30/", bill.billing_information)
		self.assertEqual(self.company_lookups, [])

	def test_tax_id_enabled_includes_company_uid(self):
		self.settings.include_tax_id_in_payment_information = 1
		self.tax_id = "CHE-123.456.789 MWST / TVA / IVA"
		bill = self.module.build_qr_bill(self.invoice)
		self.assertTrue(bill.billing_information.endswith("/30/123456789"))
		self.assertEqual(self.company_lookups, [(self.invoice.company, "tax_id")])

	def test_tax_id_enabled_without_company_uid_still_includes_invoice(self):
		self.settings.include_tax_id_in_payment_information = 1
		bill = self.module.build_qr_bill(self.invoice)
		self.assertEqual(bill.billing_information, "//S1/10/DEMO-2026-00001/11/260115")

	def test_invalid_tax_id_is_rejected_only_when_enabled(self):
		self.settings.include_tax_id_in_payment_information = 1
		self.tax_id = "DE123456789"
		with self.assertRaisesRegex(ValueError, "(?i)tax|UID|Swiss"):
			self.module.build_qr_bill(self.invoice)

	def test_single_installment_omits_counter_and_uses_invoice_date(self):
		self.per_term = True
		self.invoice.payment_schedule = [Document(
			outstanding=100, payment_amount=100, payment_term=None,
			description=None, due_date="2026-02-15",
		)]
		entry = self.module.get_qr_bill_entries(self.invoice)[0]
		bill = self.module.build_qr_bill(self.invoice, **entry)
		self.assertEqual(bill.additional_information, "Invoice DEMO-2026-00001 dated 15.01.2026")
		self.assertEqual(bill.reference, self.invoice.esr_reference_code)

	def test_multiple_installments_keep_amounts_counters_and_due_dates(self):
		self.set_installments()
		entries = self.module.get_qr_bill_entries(self.invoice)
		self.assertEqual(len(entries), 2)
		for index, entry in enumerate(entries, 1):
			bill = self.module.build_qr_bill(self.invoice, **entry)
			self.assertTrue(bill.additional_information.startswith(f"{index}/2 - Due 15.0{index + 1}.2026"))
			self.assertIn("Invoice DEMO-2026-00001", bill.additional_information)
			self.assertEqual(bill.amount, Decimal("50.00"))
			self.assertEqual(bill.reference, self.invoice.esr_reference_code)
			self.assertIn("/11/260115", bill.billing_information)

	def test_long_invoice_keeps_installments_distinct(self):
		self.set_installments()
		self.invoice.name = "SALES-INVOICE-2026-CUSTOMER-00000000000000000000000001"
		self.settings.include_tax_id_in_payment_information = 1
		self.tax_id = "CHE-123.456.789"
		messages = []
		for index, entry in enumerate(self.module.get_qr_bill_entries(self.invoice), 1):
			bill = self.module.build_qr_bill(self.invoice, **entry)
			self.assertIn(f"{index}/2 - Due 15.0{index + 1}.2026", bill.additional_information)
			self.assertLessEqual(len(bill.additional_information) + len(bill.billing_information), 140)
			self.assertIn(self.invoice.name, bill.billing_information)
			messages.append(bill.additional_information)
		self.assertNotEqual(*messages)

	def test_long_custom_message_respects_combined_limit(self):
		bill = self.module.build_qr_bill(self.invoice, additional_information="Comment " * 30)
		self.assertLessEqual(len(bill.additional_information) + len(bill.billing_information), 140)
		self.assertTrue(bill.additional_information.endswith("..."))

	def test_zero_amount_keeps_do_not_pay_warning(self):
		bill = self.module.build_qr_bill(self.invoice, amount=Decimal("0.00"))
		self.assertEqual(bill.additional_information, "DO NOT USE FOR PAYMENT")

	def test_zero_amount_rejects_overflow_after_warning_translation(self):
		self.invoice.name = "X" * 91
		with self.assertRaisesRegex(ValueError, "(?i)warning"):
			self.module.build_qr_bill(self.invoice, amount=Decimal("0.00"))

	def test_zero_amount_boundary_survives_rendering_in_each_language(self):
		# 108 characters of S1 data plus the longest 32-character warning.
		self.invoice.name = "X" * 90
		for language in ["en", "de", "fr", "it"]:
			with self.subTest(language=language):
				bill = self.module.build_qr_bill(self.invoice, amount=Decimal("0.00"))
				svg = self.module.render_qr_bill_svg(bill, language)
				self.assertEqual(bill.additional_information, ALLOWED_NOTIFICATION_TEXTS[language])
				self.assertLessEqual(len(bill.additional_information) + len(bill.billing_information), 140)
				ET.fromstring(svg)

	def test_long_svg_message_preserves_payload_and_debtor(self):
		self.invoice.name = "X"
		for message in ["W" * 121, "W" * 13 + (" " + "W" * 13) * 7, "Details & reference <test> " * 8]:
			with self.subTest(message=message):
				bill = self.module.build_qr_bill(self.invoice, additional_information=message)
				expected = bill.build_data_string()
				svg = self.module.render_qr_bill_svg(bill, "en")
				self.assertEqual(bill.build_data_string(), expected)
				root = ET.fromstring(svg)
				spans = list(root.find(f".//{SVG}text[@x='51mm']"))
				start = next(i for i, span in enumerate(spans) if span.text == "Additional information") + 1
				end = next(i for i in range(start, len(spans)) if spans[i].get("font-weight") == "bold")
				lines = [span.text for span in spans[start:end]]
				self.assertGreater(len(lines), 1)
				self.assertTrue(all(len(line) <= 24 for line in lines))
				self.assertEqual("".join("".join(lines).split()), "".join(bill.additional_information.split()))
				self.assertEqual(spans[end].text, "Payable by")
				self.assertIn(self.invoice.customer_name, [span.text for span in spans[end:]])
				last_baseline_mm = -4.76 + sum(float(span.get("dy")[:-2]) for span in spans) * 25.4 / 72
				self.assertLess(last_baseline_mm + 3, 95)

	def test_pdf_entrypoint_wraps_each_installment(self):
		self.set_installments()
		with patch.object(self.module, "svg_to_pdf", side_effect=lambda svg: svg) as converter:
			pages = self.module.generate_qr_slip_pdfs(self.invoice)
		self.assertEqual(converter.call_count, 2)
		for index, svg in enumerate(pages, 1):
			self.assertIn("50.00", svg)
			spans = list(ET.fromstring(svg).find(f".//{SVG}text[@x='51mm']"))
			self.assertGreater(len(spans), 14)
			self.assertIn(f"{index}/2", " ".join(span.text or "" for span in spans))


if __name__ == "__main__":
	unittest.main()
