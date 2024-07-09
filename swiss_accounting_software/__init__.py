# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
import cgi
from frappe.utils.file_manager import save_file
from .utils import is_expense, get_expenses, getAccountNumber, docs, data, taxes, rounding_off, document_number, invoice as inv_f, amount as inv_amt, write_off, reset_docs, reset_accounts, payment_entry_amount

__version__ = '0.0.6'


def gl(company, start_date, end_date):
    """
    Abacus XML
    """

    transactions = []
    doc_invoices = []

    invoices = docs('Sales Invoice', start_date, end_date)
    purchaseInvoices = docs('Purchase Invoice', start_date, end_date)
    paymentEntry = docs('Payment Entry', start_date, end_date)

    sales_invoice_no = len(invoices)
    purchase_invoice_no = len(purchaseInvoices)
    payment_entry_no = len(paymentEntry)

    # Sales Invoice

    for invoice in invoices:
        inv = frappe.get_doc('Sales Invoice', invoice.name)

        tax_code, taxAccount, rate, taxAccountNumber = taxes(
            "Sales Taxes and Charges Template", inv)

        currency = frappe.get_doc('Company', inv.company).default_currency

        invoice = inv_f(inv, inv.debit_to, 'D', currency, taxAccountNumber)

        # Round Off Account
        rounding_adjustment = rounding_off(inv)

        if rounding_adjustment:
            invoice['against_singles'].append(rounding_adjustment)

        # Items
        for item in inv.items:
            invoice['against_singles'].append(
                inv_amt(item, item.income_account, inv.currency,
                        taxAccount, rate, tax_code, currency)
            )

        if inv.write_off_amount != 0:
            invoice['against_singles'].append(write_off(inv))

        # Taxes
        for tax in inv.taxes:
            if is_expense(tax.item_wise_tax_detail):
                for item in get_expenses(tax):
                    invoice['against_singles'].append({
                        'account':  getAccountNumber(item['account']),
                        'amount': item['amount'],
                        'currency': inv.currency,
                        'tax_account': getAccountNumber(taxAccount) if taxAccount else None,
                        'tax_amount': tax.tax_amount or None,
                        'tax_rate':  tax.rate or None,
                        'tax_code': tax.steuerziffer_ch if tax.steuerziffer_ch != None else tax_code,
                        'tax_currency': tax.account_currency or None,
                        'keyamount': tax.tax_amount if tax.charge_type == "Actual" else 0,
                    })

        doc_invoices.append(invoice)

    # Purchase Invoice
    for invoice in purchaseInvoices:
        inv = frappe.get_doc('Purchase Invoice', invoice.name)

        tax_code, taxAccount, rate, taxAccountNumber = taxes(
            "Purchase Taxes and Charges Template", inv)

        currency = frappe.get_doc('Company', inv.company).default_currency

        invoice = inv_f(inv, inv.credit_to, 'C', currency, taxAccountNumber)

        # Rounding Off
        rounding_adjustment = rounding_off(inv)

        if rounding_adjustment:
            invoice['against_singles'].append(rounding_adjustment)

        # Item
        for item in inv.items:
            invoice['against_singles'].append(
                inv_amt(item, item.expense_account, inv.currency,
                        taxAccount, rate, tax_code, currency)
            )

        if inv.write_off_amount != 0:
            invoice['against_singles'].append(write_off(inv))

        for tax in inv.taxes:
            if is_expense(tax.item_wise_tax_detail):
                for item in get_expenses(tax):
                    invoice['against_singles'].append({
                        'account':  getAccountNumber(item['account']),
                        'amount': item['amount'],
                        'currency': inv.currency,
                        'tax_account': getAccountNumber(taxAccount) if taxAccount else None,
                        'tax_amount': tax.tax_amount or None,
                        'tax_rate':  tax.rate or None,
                        'tax_code': tax.steuerziffer_ch if tax.steuerziffer_ch != None else tax_code,
                        'tax_currency': tax.account_currency or None,
                        'keyamount': tax.tax_amount if tax.charge_type == "Actual" else 0,
                        'expense_account': tax.expense_account if tax.expense_account else None
                    })


        doc_invoices.append(invoice)

    # Payment Entry

    for invoice in paymentEntry:
        inv = frappe.get_doc('Payment Entry', invoice.name)

        transaction = {
            'account': getAccountNumber(inv.paid_from),
            'amount': payment_entry_amount(inv),
            'against_singles': [{
                'account':  getAccountNumber(inv.paid_to),
                'amount': inv.paid_amount,
                'currency': inv.paid_from_account_currency
            }],
            'debit_credit': 'C',
            'date': inv.posting_date,
            'exchange_rate': inv.target_exchange_rate,
            'currency': inv.paid_to_account_currency,
            'key_currency': inv.paid_from_account_currency,
            'tax_account': None,
            'tax_amount': None,
            'tax_rate': None,
            'tax_code': 0,
            'text1': inv.name,
            'document_number': document_number(inv.name)
        }

        for deduction in inv.deductions:
            transaction['against_singles'].append({
                'account': getAccountNumber(deduction.account),
                'amount': deduction.amount,
                'currency': inv.paid_from_account_currency
            })

        transactions.append(transaction)

    # Set Accounts
    reset_accounts('Sales Invoice', invoices, 1)
    reset_accounts('Purchase Invoice', purchaseInvoices, 1)
    reset_accounts('Payment Entry', paymentEntry, 1)

    return frappe.render_template('abacus.html', data(doc_invoices, transactions, start_date, end_date, sales_invoice_no, purchase_invoice_no, payment_entry_no))


def attach(company, start_date, end_date, doctype, name):
    gl_xml = gl(company, start_date, end_date)
    save_file('abacus.xml', gl_xml, doctype, name, is_private=True)


def attach_xml(doc, event=None):
    """
    Attach XML File to Doctype
    """
    attach(doc.company, doc.start_date, doc.end_date, doc.doctype, doc.name)


@frappe.whitelist()
def reset_account(company, start_date, end_date, doctype, docname):
    """
    Reset and Re Attach
    """
    reset_docs(start_date, end_date)
    return {
        'file': gl(company, start_date, end_date)
    }
