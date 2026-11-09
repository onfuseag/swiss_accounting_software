"""Security regressions for the manual QR PDF attachment endpoint."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parents[1] / "swiss_accounting_software" / "attach_pdf.py"


class AttachPdfSecurityTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe = ModuleType("frappe")
		frappe._ = lambda message: message
		frappe.get_doc = Mock()
		frappe.get_all = Mock()
		frappe.delete_doc = Mock()
		def whitelist(**options):
			def decorate(func):
				func.allowed_methods = options.get("methods")
				return func
			return decorate
		frappe.whitelist = whitelist
		frappe.db = SimpleNamespace()
		frappe.local = SimpleNamespace(lang="en")

		utils = ModuleType("frappe.utils")
		file_manager = ModuleType("frappe.utils.file_manager")
		file_manager.save_file = Mock()
		pdf4 = ModuleType("PyPDF4")
		pdf4.PdfFileMerger = Mock()
		package = ModuleType("swiss_accounting_software")
		package.__path__ = []
		qr_bill = ModuleType("swiss_accounting_software.qr_bill")
		qr_bill.generate_qr_slip_pdfs = Mock()

		with patch.dict(sys.modules, {
			"frappe": frappe,
			"frappe.utils": utils,
			"frappe.utils.file_manager": file_manager,
			"PyPDF4": pdf4,
			"swiss_accounting_software": package,
			"swiss_accounting_software.qr_bill": qr_bill,
		}):
			spec = importlib.util.spec_from_file_location("attach_pdf_security_under_test", SOURCE)
			cls.module = importlib.util.module_from_spec(spec)
			spec.loader.exec_module(cls.module)

	def test_read_only_user_cannot_regenerate_or_delete_files(self):
		invoice = SimpleNamespace(check_permission=Mock(side_effect=PermissionError("write denied")))
		with patch.object(self.module.frappe, "get_doc", return_value=invoice), \
			patch.object(self.module, "generate_qr_slip_pdfs") as generate, \
			patch.object(self.module, "remove_existing_qr_pdf") as remove:
			with self.assertRaisesRegex(PermissionError, "write denied"):
				self.module.attach_pdf("INV-001")
			invoice.check_permission.assert_called_once_with("write")
			generate.assert_not_called()
			remove.assert_not_called()

	def test_replacement_only_deletes_private_qr_files(self):
		files = [
			SimpleNamespace(name="plain", file_name="INV-001-QR.pdf"),
			SimpleNamespace(name="hashed", file_name="INV-001-QR012abc.pdf"),
			SimpleNamespace(name="other", file_name="INV-001-QR-terms.pdf"),
			SimpleNamespace(name="backup", file_name="INV-001-QR.pdf.bak"),
		]
		with patch.object(self.module.frappe, "get_all", return_value=files) as get_all, \
			patch.object(self.module.frappe, "delete_doc") as delete:
			self.module.remove_existing_qr_pdf("Sales Invoice", "INV-001")
			self.assertEqual(
				delete.call_args_list,
				[
					unittest.mock.call("File", "plain", ignore_permissions=False),
					unittest.mock.call("File", "hashed", ignore_permissions=False),
				],
			)
			self.assertEqual(get_all.call_args.kwargs["filters"]["is_private"], 1)

	def test_writer_can_regenerate_without_bypassing_file_permissions(self):
		invoice = SimpleNamespace(check_permission=Mock())
		with patch.object(self.module.frappe, "get_doc", return_value=invoice), \
			patch.object(self.module, "generate_qr_slip_pdfs", return_value=[b"qr"]), \
			patch.object(self.module, "get_pdf_data", return_value=b"invoice"), \
			patch.object(self.module, "merge_pdf", return_value=b"merged"), \
			patch.object(self.module, "remove_existing_qr_pdf") as remove, \
			patch.object(self.module, "save_and_attach") as attach:
			self.module.attach_pdf("INV-001")
			invoice.check_permission.assert_called_once_with("write")
			remove.assert_called_once_with("Sales Invoice", "INV-001", ignore_permissions=False)
			attach.assert_called_once_with(b"merged", "Sales Invoice", "INV-001")

	def test_submit_hook_retains_trusted_permission_bypass(self):
		invoice = SimpleNamespace(check_permission=Mock())
		with patch.object(self.module.frappe, "get_doc", return_value=invoice), \
			patch.object(self.module, "generate_qr_slip_pdfs", return_value=[b"qr"]), \
			patch.object(self.module, "get_pdf_data", return_value=b"invoice"), \
			patch.object(self.module, "merge_pdf", return_value=b"merged"), \
			patch.object(self.module, "remove_existing_qr_pdf") as remove, \
			patch.object(self.module, "save_and_attach") as attach:
			self.module.attach_qr_bill("INV-001", ignore_permissions=True)
			invoice.check_permission.assert_not_called()
			remove.assert_called_once_with("Sales Invoice", "INV-001", ignore_permissions=True)
			attach.assert_called_once_with(b"merged", "Sales Invoice", "INV-001")

	def test_manual_endpoint_only_accepts_post(self):
		self.assertEqual(self.module.attach_pdf.allowed_methods, ["POST"])


if __name__ == "__main__":
	unittest.main()
