import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """ Make sure that the accounting dimension for Steuerziffer CH already exists"""
    create_steuerziffer_dimension()

    """ Create custom fields in doctypes """
    create_custom_fields(get_custom_fields(), ignore_validate=True)

def create_steuerziffer_dimension():
    if not frappe.db.exists("Accounting Dimension", {"document_type": "Steuerziffer CH"}):
        
        doc = frappe.get_doc({
            "doctype": "Accounting Dimension",
            "document_type": "Steuerziffer CH",
            "label": "Steuerziffer CH"
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()

def get_custom_fields():
    return {
        "Bank Statement Import": [
            {
                "fieldname": "custom_column_break_11",
                "fieldtype": "Column Break",
                "insert_after": "template_options",
                "depends_on": "eval:!doc.__islocal"
            },
            {
                "fieldname": "custom_camt",
                "fieldtype": "Check",
                "label": "CAMT",
                "insert_after": "custom_column_break_11",
                "depends_on": "eval:!doc.__islocal"
            },
            {
                "fieldname": "custom_camt_xml_file",
                "fieldtype": "Attach",
                "label": "CAMT XML File",
                "insert_after": "custom_camt",
                "depends_on": "eval:!doc.__islocal && doc.custom_camt"
            },
            {
                "fieldname": "custom_convert_xml_to_csv",
                "fieldtype": "Button",
                "label": "Convert XML to CSV",
                "insert_after": "custom_camt_xml_file",
                "depends_on": "eval:!doc.__islocal && doc.custom_camt_xml_file"
            },
        ], 
        "Sales Invoice": [
            {
                "fieldname": "esr_reference_code",
                "fieldtype": "Data",
                "insert_after": "po_date",
                "label": "ESR Reference Code",
                "length": 27,
                "unique": 1,
            }
        ], 
    }