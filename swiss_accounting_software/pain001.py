import frappe
import cgi
from frappe.utils.file_manager import save_file


# Starts the generation of an XML File for pain.001 and attaches it to the doctype "Payment order"
def generate_pain001_xml(doc):

    # Get the bank account and check if it contains the correct data
    bank_account = frappe.get_doc("Bank Account", doc.company_bank)

    if bank_account.iban is None or bank_account.branch_code is None: 
        frappe.throw("No IBAN or Branch code set for this bank account")

    payments= 
    
    
    return frappe.render_template("pain001.html", data(doc, bank_account, payments))


def generate_template_xml(doc):
    # Get the bank account and check if it contains the correct data
    bank_account = frappe.get_doc("Bank Account", doc.company_bank)

    if bank_account.iban is None or bank_account.branch_code is None: 
        frappe.throw("No IBAN or Branch code set for this bank account")
    
    
    return frappe.render_template("pain001.html", data(doc, bank_account, payments))

@frappe.whitelist()
def get_qr_code_from_file(file):
    