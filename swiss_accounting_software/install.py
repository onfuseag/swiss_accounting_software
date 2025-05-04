import frappe

def after_install():
    """ Make sure that the accounting dimension for Steuerziffer CH already exists"""
    create_steuerziffer_dimension()

def create_steuerziffer_dimension():
    if not frappe.db.exists("Accounting Dimension", {"document_type": "Steuerziffer CH"}):
        
        doc = frappe.get_doc({
            "doctype": "Accounting Dimension",
            "document_type": "Steuerziffer CH",
            "label": "Steuerziffer CH"
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()