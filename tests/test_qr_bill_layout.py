"""Check that printed QR slips contain the structured billing information."""

from decimal import Decimal
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from chqr import Creditor, QRBill, UltimateDebtor
from chqr.constants import TRANSLATIONS


SOURCE = Path(__file__).resolve().parents[1] / "swiss_accounting_software" / "qr_bill_layout.py"
spec = importlib.util.spec_from_file_location("qr_bill_layout_under_test", SOURCE)
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
SVG = "{http://www.w3.org/2000/svg}"


class PrintedBillingInformationTests(unittest.TestCase):
	def make_bill(self, information, message=None):
		return QRBill(
			account="CH4431999123000889012",
			creditor=Creditor(name="Example Company", postal_code="3000", city="Bern",
				country="CH", street="Example Street", building_number="1"),
			debtor=UltimateDebtor(name="Example Customer", postal_code="8000", city="Zürich",
				country="CH", street="Customer Street", building_number="2"),
			currency="CHF", amount=Decimal("100.00"), reference_type="QRR",
			reference="210000000003139471430009017",
			additional_information=message, billing_information=information,
		)

	def payment_spans(self, svg):
		root = ET.fromstring(svg)
		parent = root.find(f".//{SVG}text[@x='51mm'][@y='-4.76mm']")
		self.assertIsNotNone(parent)
		return list(parent)

	def assert_fits_payment_part(self, spans):
		last_baseline_mm = -4.76 + sum(float(span.get("dy")[:-2]) for span in spans) * 25.4 / 72
		self.assertLess(last_baseline_mm + 3, 95)

	def test_s1_alone_uses_translated_heading_in_each_language(self):
		information = "//S1/10/DEMO-2026-00001/11/260115"
		for language, labels in TRANSLATIONS.items():
			with self.subTest(language=language):
				bill = self.make_bill(information)
				payload = bill.build_data_string()
				svg = layout.wrap_additional_information(
					bill.generate_svg(language=language), bill.additional_information, information)
				spans = self.payment_spans(svg)
				texts = [span.text for span in spans]
				self.assertEqual(texts.count(labels["additional_information"]), 1)
				start = texts.index(labels["additional_information"]) + 1
				end = texts.index(labels["payable_by"])
				self.assertEqual("".join(texts[start:end]), information)
				self.assertEqual(bill.build_data_string(), payload)
				self.assert_fits_payment_part(spans)

	def test_long_s1_is_complete_and_fits_with_reference_and_debtor(self):
		information = "//S1/10/" + "X" * 122 + "/11/260115"
		self.assertEqual(len(information), 140)
		bill = self.make_bill(information)
		spans = self.payment_spans(layout.wrap_additional_information(
			bill.generate_svg(language="de"), bill.additional_information, information))
		start = next(i for i, span in enumerate(spans) if span.text == "Zusätzliche Informationen") + 1
		end = next(i for i in range(start, len(spans)) if spans[i].get("font-weight") == "bold")
		self.assertEqual("".join(span.text for span in spans[start:end]), information)
		self.assertTrue(all(len(span.text) <= layout.MESSAGE_LINE_LENGTH for span in spans[start:end]))
		self.assertEqual(spans[end].text, "Zahlbar durch")
		self.assert_fits_payment_part(spans)

	def test_message_and_s1_share_one_heading_and_escape_xml(self):
		message = "Installment 1/2 - 15.02.2026"
		information = "//S1/10/INV & <A B>\\/42/11/260115"
		bill = self.make_bill(information, message)
		spans = self.payment_spans(layout.wrap_additional_information(
			bill.generate_svg(language="fr"), bill.additional_information, information))
		texts = [span.text for span in spans]
		self.assertEqual(texts.count("Informations supplémentaires"), 1)
		start = texts.index("Informations supplémentaires") + 1
		end = texts.index("Payable par")
		message_end = start + len(layout._message_lines(message))
		self.assertEqual("".join("".join(texts[start:message_end]).split()), "".join(message.split()))
		self.assertEqual("".join(texts[message_end:end]), information)
		self.assert_fits_payment_part(spans)

	def test_word_wrapping_cannot_push_debtor_off_the_payment_part(self):
		message = " ".join(["W" * 13] * 8)
		information = "//S1/10/" + "X" * 11 + "/11/260115"
		self.assertEqual(len(message) + len(information), 140)
		bill = self.make_bill(information, message)
		spans = self.payment_spans(layout.wrap_additional_information(
			bill.generate_svg(language="en"), bill.additional_information, information))
		texts = [span.text for span in spans]
		start = texts.index("Additional information") + 1
		end = texts.index("Payable by")
		message_end = start + len(layout._message_lines(message, 2))
		self.assertEqual("".join(texts[start:message_end]), message)
		self.assertEqual("".join(texts[message_end:end]), information)
		self.assert_fits_payment_part(spans)


if __name__ == "__main__":
	unittest.main()
