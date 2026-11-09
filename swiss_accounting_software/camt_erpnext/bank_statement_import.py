"""Convert an accessible CAMT attachment for ERPNext's bank statement importer."""

import csv
from io import BytesIO, StringIO
from pathlib import PurePosixPath
from urllib.parse import unquote
import xml.etree.ElementTree as ET

import frappe
from frappe.core.doctype.file.utils import find_file_by_url
from frappe.utils.csvutils import escape_formula_injection
from frappe.utils.file_manager import save_file


def remove_namespaces(xml_source):
    """Parse XML while removing namespaces from element names."""
    parsed = ET.iterparse(xml_source, events=("start",))
    for _, element in parsed:
        if "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]
    return parsed.root


def _safe_csv_cell(value):
    # Frappe's CSV importer also strips cells before undoing this escaping.
    # Strip first so leading whitespace cannot hide a spreadsheet formula.
    return escape_formula_injection(value.strip() if isinstance(value, str) else value)


def _readable_xml_file(file_url):
    if not isinstance(file_url, str) or not file_url.startswith(
        ("/files/", "/private/files/")
    ):
        frappe.throw("A local CAMT attachment is required.", frappe.PermissionError)

    # Frappe's File.get_content validates the real filesystem path as well.
    # Reject traversal here even when the caller supplies an encoded path.
    if ".." in PurePosixPath(unquote(file_url)).parts:
        frappe.throw("Invalid CAMT attachment path.", frappe.PermissionError)

    file_doc = find_file_by_url(file_url)
    if not file_doc:
        frappe.throw("You do not have access to this CAMT attachment.", frappe.PermissionError)
    file_doc.check_permission("read")
    return file_doc


@frappe.whitelist(methods=["POST"])
def convert_xml_to_csv(file, data_import):
    import_doc = frappe.get_doc("Bank Statement Import", data_import)
    import_doc.check_permission("write")

    # A File record must exist and be readable; a bare private path is never enough.
    xml_content = _readable_xml_file(file).get_content(encodings=())
    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")
    root = remove_namespaces(BytesIO(xml_content))

    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        ["Date", "Bank Account", "Company", "Deposit", "Withdrawal", "Reference Number", "Description"]
    )

    for entry in root.findall(".//Ntfctn/Ntry"):
        date = entry.find(".//BookgDt/Dt").text
        bank_account = root.find(".//Acct/Id/IBAN").text

        for transaction in entry.findall(".//TxDtls"):
            debtor = transaction.find(".//Dbtr/Pty/Nm")
            description = f"Payment from {debtor.text if debtor is not None else 'Unknown'}"
            amount = transaction.find(".//Amt").text
            direction = transaction.find(".//CdtDbtInd").text
            reference = transaction.find(".//CdtrRefInf/Ref").text
            deposit = amount if direction == "CRDT" else ""
            withdrawal = amount if direction != "CRDT" else ""
            writer.writerow(
                [
                    _safe_csv_cell(value)
                    for value in (
                        date,
                        bank_account,
                        "",
                        deposit,
                        withdrawal,
                        reference,
                        description,
                    )
                ]
            )

    content = output.getvalue().encode("utf-8")
    saved_file = save_file(
        f"camt-{frappe.generate_hash(length=10)}.csv",
        content,
        import_doc.doctype,
        import_doc.name,
        is_private=True,
        df="import_file",
    )
    return saved_file.file_url
