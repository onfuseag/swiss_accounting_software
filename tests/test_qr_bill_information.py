"""Contrôle des vrais contenus chqr, avec accès Frappe simulés et données inventées."""

from datetime import date, datetime
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[1] / "swiss_accounting_software"


def load_source(name):
	# L'initialisation de l'application importe Frappe et ses modules métier.
	# Les tests ciblés chargent les fichiers réels sans initialiser un site.
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
	def test_invoice_date_and_s1_are_distinct_from_payment_reference(self):
		self.assertEqual(billing_information("DEMO-2026-00001", "2026-01-15"), "//S1/10/DEMO-2026-00001/11/260115")

	def test_reserved_separators_are_escaped_without_changing_identity(self):
		self.assertEqual(billing_information("DEMO/1\\2", date(2026, 1, 15)), "//S1/10/DEMO\\/1\\\\2/11/260115")

	def test_swiss_tax_id_is_included_when_known(self):
		self.assertEqual(billing_information("DEMO", "2026-01-15", "CHE-123.456.789 TVA"), "//S1/10/DEMO/11/260115/30/123456789")

	def test_invalid_metadata_is_rejected_without_silent_changes(self):
		for number, day, tax in [("", "2026-01-15", None), ("DEMO\nEPD", "2026-01-15", None), ("DEMO", "2026-02-30", None), ("DEMO", "2026-01-15", "invalid"), ("X" * 140, "2026-01-15", None)]:
			with self.subTest(number=number), self.assertRaises(ValueError):
				billing_information(number, day, tax)

	def test_combined_limit_preserves_structured_information(self):
		information = billing_information("DEMO", "2026-01-15")
		remaining = 140 - len(information)
		self.assertEqual(fit_message("X" * remaining, information), "X" * remaining)
		message = fit_message("X" * (remaining + 1), information)
		self.assertEqual(len(message) + len(information), 140)
		self.assertTrue(message.endswith("..."))
		self.assertIsNone(fit_message("Texte", "X" * 140))

	def test_readable_dates_are_localised(self):
		self.assertEqual(invoice_message("DEMO", datetime(2026, 1, 15), "fr"), "Facture DEMO du 15.01.2026")
		self.assertEqual(invoice_message("DEMO", "2026-01-15", "en"), "Invoice DEMO dated 15.01.2026")


class QRBillIntegrationTests(unittest.TestCase):
	def setUp(self):
		self.reference_type = "QRR"
		self.per_term = False
		self.tax_id = None
		self.address = Document(address_line1="Teststrasse", address_line2="1", pincode="3000", city="Bern", country="Switzerland")
		self.settings = Document(bank_account="Compte exemple", qr_code_type="QRR")
		frappe = ModuleType("frappe")
		frappe._ = lambda value: value
		frappe.db = SimpleNamespace(exists=lambda *args: True, get_value=self.get_value)
		frappe.get_doc = lambda kind, name: self.settings if kind == "Swiss QR Bill Settings" else self.address
		def throw(message):
			raise ValueError(message)
		frappe.throw = throw
		path = Path(__file__).resolve().parents[1] / "swiss_accounting_software" / "qr_bill.py"
		spec = importlib.util.spec_from_file_location("qr_bill_under_test", path)
		self.module = importlib.util.module_from_spec(spec)
		package = ModuleType("swiss_accounting_software")
		package.__path__ = [str(SOURCE)]
		with patch.dict(sys.modules, {"frappe": frappe, "swiss_accounting_software": package}):
			spec.loader.exec_module(self.module)
		self.invoice = Document(name="DEMO-2026-00001", posting_date="2026-01-15", language="en", company="Société exemple", company_address="Adresse société", customer_address="Adresse exemple", customer_name="Client exemple", customer="CLIENT-DEMO", outstanding_amount=Decimal("100.00"), currency="CHF", esr_reference_code="210000000003139471430009017", payment_schedule=[])

	def get_value(self, kind, name, field):
		if kind == "Country":
			return "CH"
		if kind == "Bank Account":
			return "CH4431999123000889012" if self.settings.qr_code_type == "QRR" else "CH9300762011623852957"
		if kind == "Company":
			return self.tax_id
		if field == "qr_bill_per_invoice":
			return self.per_term
		return self.settings.qr_code_type

	def test_real_payload_keeps_qrr_and_adds_two_separate_fields(self):
		bill = self.module.build_qr_bill(self.invoice)
		fields = bill.build_data_string().split("\n")
		self.assertEqual(fields[27:32], ["QRR", "210000000003139471430009017", "Invoice DEMO-2026-00001 dated 15.01.2026", "EPD", "//S1/10/DEMO-2026-00001/11/260115"])
		self.assertEqual(bill.amount, Decimal("100.00"))
		self.assertIn("DEMO-2026-00001", bill.generate_svg(language="en"))
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
				self.assertTrue(bill.billing_information.startswith("//S1/10/"))

	def test_single_term_removes_counter_and_uses_invoice_date(self):
		self.per_term = True
		self.invoice.payment_schedule = [Document(outstanding=100, payment_amount=100, payment_term=None, description=None, due_date="2026-02-15")]
		entry = self.module.get_qr_bill_entries(self.invoice)[0]
		self.assertEqual(entry["additional_information"], "Invoice DEMO-2026-00001 dated 15.01.2026")
		self.assertEqual(self.module.build_qr_bill(self.invoice, **entry).reference, self.invoice.esr_reference_code)

	def test_multiple_terms_keep_amounts_counters_and_due_dates(self):
		self.per_term = True
		self.invoice.payment_schedule = [Document(outstanding=50, payment_amount=50, payment_term="Versement", description=None, due_date=day) for day in ["2026-02-15", "2026-03-15"]]
		entries = self.module.get_qr_bill_entries(self.invoice)
		for index, entry in enumerate(entries, 1):
			self.assertTrue(entry["additional_information"].startswith("Invoice DEMO-2026-00001"))
			self.assertIn(f"{index}/2 - Versement", entry["additional_information"])
			self.assertIn(self.invoice.payment_schedule[index - 1].due_date, entry["additional_information"])
			bill = self.module.build_qr_bill(self.invoice, **entry)
			self.assertEqual(bill.amount, Decimal("50.00"))
			self.assertEqual(bill.reference, self.invoice.esr_reference_code)
			self.assertIn("/11/260115", bill.billing_information)

	def test_long_message_respects_combined_limit_in_real_payload(self):
		bill = self.module.build_qr_bill(self.invoice, additional_information="Commentaire " * 30)
		self.assertLessEqual(len(bill.additional_information) + len(bill.billing_information), 140)
		self.assertTrue(bill.additional_information.endswith("..."))

	def test_zero_amount_keeps_do_not_pay_warning(self):
		bill = self.module.build_qr_bill(self.invoice, amount=Decimal("0.00"))
		self.assertEqual(bill.additional_information, "DO NOT USE FOR PAYMENT")

	def test_existing_tax_number_reaches_structured_payload(self):
		self.tax_id = "CHE-123.456.789"
		self.assertTrue(self.module.build_qr_bill(self.invoice).billing_information.endswith("/30/123456789"))

	def test_zero_amount_rejects_metadata_that_overflows_a_translated_warning(self):
		# Le rendu chqr traduit l'avertissement après la création de QRBill.
		self.invoice.name = "X" * 91
		for language in ["en", "de", "fr", "it"]:
			with self.subTest(language=language):
				self.invoice.language = language
				with self.assertRaisesRegex(ValueError, "avertissement"):
					self.module.build_qr_bill(self.invoice, amount=Decimal("0.00"))

	def test_zero_amount_boundary_is_valid_after_each_language_render(self):
		# 108 caractères S1 + 32 caractères pour le plus long avertissement.
		self.invoice.name = "X" * 90
		bill = self.module.build_qr_bill(self.invoice, amount=Decimal("0.00"))
		for language in ["en", "de", "fr", "it"]:
			with self.subTest(language=language):
				bill.generate_svg(language=language)
				self.assertLessEqual(len(bill.additional_information) + len(bill.billing_information), 140)

	def test_printed_long_message_wraps_without_changing_qr_or_hiding_debtor(self):
		self.invoice.name = "X"
		for message in ["W" * 121, "W" * 13 + (" " + "W" * 13) * 7, "Échéance & détail <test> " * 8]:
			with self.subTest(message=message):
				bill = self.module.build_qr_bill(self.invoice, additional_information=message)
				expected = bill.build_data_string()
				svg = self.module.render_qr_bill_svg(bill, "en")
				self.assertEqual(bill.build_data_string(), expected)
				root = ET.fromstring(svg)
				parent = root.find(".//{http://www.w3.org/2000/svg}text[@x='51mm']")
				spans = list(parent)
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

	def test_pdf_entrypoint_uses_wrapped_svg_for_each_installment(self):
		self.per_term = True
		self.invoice.payment_schedule = [Document(outstanding=50, payment_amount=50, payment_term="Versement", description=None, due_date=day) for day in ["2026-02-15", "2026-03-15"]]
		with patch.object(self.module, "svg_to_pdf", side_effect=lambda svg: svg) as converter:
			pages = self.module.generate_qr_slip_pdfs(self.invoice)
		self.assertEqual(converter.call_count, 2)
		for svg in pages:
			self.assertIn("50.00", svg)
			root = ET.fromstring(svg)
			parent = root.find(".//{http://www.w3.org/2000/svg}text[@x='51mm']")
			self.assertGreater(len(list(parent)), 14)


if __name__ == "__main__":
	unittest.main()
