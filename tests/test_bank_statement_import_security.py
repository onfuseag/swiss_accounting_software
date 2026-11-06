"""Security regression tests for CAMT conversion without a running Frappe site."""

import csv
from io import StringIO
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / (
    "swiss_accounting_software/camt_erpnext/bank_statement_import.py"
)


def make_camt(reference="REF-123", amount="12.34"):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022">
  <Ntfctn>
    <Acct><Id><IBAN>CH123</IBAN></Id></Acct>
    <Ntry>
      <BookgDt><Dt>2026-11-06</Dt></BookgDt>
      <TxDtls>
        <Dbtr><Pty><Nm>Test Payer</Nm></Pty></Dbtr>
        <Amt>{amount}</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <CdtrRefInf><Ref>{reference}</Ref></CdtrRefInf>
      </TxDtls>
    </Ntry>
  </Ntfctn>
</Document>""".encode()


class StubPermissionError(Exception):
    pass


class StubDocument:
    doctype = "Bank Statement Import"
    name = "BSI-001"

    def __init__(self, allowed=True):
        self.allowed = allowed
        self.checked = []

    def check_permission(self, permission):
        self.checked.append(permission)
        if not self.allowed:
            raise StubPermissionError


class StubFile:
    def __init__(self, content, allowed=True):
        self.content = content
        self.allowed = allowed
        self.checked = []
        self.reads = 0

    def check_permission(self, permission):
        self.checked.append(permission)
        if not self.allowed:
            raise StubPermissionError

    def get_content(self, *, encodings=None):
        self.reads += 1
        if encodings != ():
            raise AssertionError("XML must be read as raw bytes")
        return self.content


class TestBankStatementImportSecurity(unittest.TestCase):
    def setUp(self):
        self.import_doc = StubDocument()
        self.file_doc = StubFile(make_camt())
        self.source_url = "/private/files/camt.xml"
        self.saved = []
        self.lookups = []

        frappe = types.ModuleType("frappe")
        frappe.PermissionError = StubPermissionError
        frappe.get_doc = lambda doctype, name: self.import_doc
        frappe.generate_hash = lambda length=10: "fixedhash"

        def throw(message, exception=Exception):
            raise exception(message)

        frappe.throw = throw

        def whitelist(*, methods=None):
            def decorate(func):
                func.allowed_methods = methods
                return func

            return decorate

        frappe.whitelist = whitelist

        def find_file_by_url(url):
            self.lookups.append(url)
            return self.file_doc if url == self.source_url else None

        def escape_formula_injection(value):
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                return "'" + value
            return value

        def save_file(filename, content, doctype, docname, *, is_private, df):
            self.saved.append((filename, content, doctype, docname, is_private, df))
            return types.SimpleNamespace(file_url="/private/files/camt-fixedhash.csv")

        file_utils = types.ModuleType("frappe.core.doctype.file.utils")
        file_utils.find_file_by_url = find_file_by_url
        csvutils = types.ModuleType("frappe.utils.csvutils")
        csvutils.escape_formula_injection = escape_formula_injection
        file_manager = types.ModuleType("frappe.utils.file_manager")
        file_manager.save_file = save_file

        self.patch_modules = patch.dict(
            sys.modules,
            {
                "frappe": frappe,
                "frappe.core": types.ModuleType("frappe.core"),
                "frappe.core.doctype": types.ModuleType("frappe.core.doctype"),
                "frappe.core.doctype.file": types.ModuleType("frappe.core.doctype.file"),
                "frappe.core.doctype.file.utils": file_utils,
                "frappe.utils": types.ModuleType("frappe.utils"),
                "frappe.utils.csvutils": csvutils,
                "frappe.utils.file_manager": file_manager,
            },
        )
        self.patch_modules.start()
        self.addCleanup(self.patch_modules.stop)

        spec = importlib.util.spec_from_file_location("camt_security_under_test", MODULE_PATH)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_requires_write_access_to_import_document(self):
        self.import_doc.allowed = False
        with self.assertRaises(StubPermissionError):
            self.module.convert_xml_to_csv(self.source_url, self.import_doc.name)
        self.assertEqual(self.import_doc.checked, ["write"])
        self.assertEqual(self.lookups, [])
        self.assertEqual(self.saved, [])

    def test_requires_a_readable_file_record(self):
        with self.assertRaises(StubPermissionError):
            self.module.convert_xml_to_csv("/private/files/other.xml", self.import_doc.name)
        self.assertEqual(self.saved, [])

        self.file_doc.allowed = False
        with self.assertRaises(StubPermissionError):
            self.module.convert_xml_to_csv(self.source_url, self.import_doc.name)
        self.assertEqual(self.file_doc.checked, ["read"])
        self.assertEqual(self.file_doc.reads, 0)
        self.assertEqual(self.saved, [])

    def test_rejects_traversal_and_remote_urls_before_lookup(self):
        for url in (
            "/private/files/../../other/private/files/bank.xml",
            "/private/files/%2e%2e/bank.xml",
            "/private/other.xml",
            "https://example.invalid/bank.xml",
        ):
            with self.subTest(url=url), self.assertRaises(StubPermissionError):
                self.module.convert_xml_to_csv(url, self.import_doc.name)
        self.assertEqual(self.lookups, [])
        self.assertEqual(self.saved, [])

    def test_escapes_formula_values_and_returns_owned_private_file(self):
        self.file_doc.content = make_camt(reference="  =HYPERLINK(&quot;evil&quot;)", amount="-12.34")
        result = self.module.convert_xml_to_csv(self.source_url, self.import_doc.name)
        self.assertEqual(result, "/private/files/camt-fixedhash.csv")
        self.assertEqual(self.file_doc.checked, ["read"])
        self.assertEqual(self.file_doc.reads, 1)
        filename, content, doctype, docname, is_private, fieldname = self.saved[0]
        self.assertEqual((filename, doctype, docname, is_private, fieldname),
                         ("camt-fixedhash.csv", "Bank Statement Import", "BSI-001", True, "import_file"))
        row = list(csv.reader(StringIO(content.decode("utf-8"))))[1]
        self.assertEqual(row[3], "'-12.34")
        self.assertEqual(row[5], "'=HYPERLINK(\"evil\")")
        self.assertEqual(row[3][1:], "-12.34")
        self.assertEqual(row[5][1:], '=HYPERLINK("evil")')
        self.assertEqual(self.module.convert_xml_to_csv.allowed_methods, ["POST"])

    def test_all_formula_prefixes_and_leading_whitespace(self):
        for value, expected in (
            ("=1+1", "'=1+1"),
            ("+SUM(1)", "'+SUM(1)"),
            ("-12.34", "'-12.34"),
            ("@A1", "'@A1"),
            ("  =1+1", "'=1+1"),
            ("\t=1+1", "'=1+1"),
            ("\r=1+1", "'=1+1"),
        ):
            with self.subTest(value=value):
                self.assertEqual(self.module._safe_csv_cell(value), expected)


if __name__ == "__main__":
    unittest.main()
