import json
from werkzeug.wrappers import Response
from frappe.utils.file_manager import save_file
import frappe


def is_expense(txt):
    """
    Check Weather Entry in Tax
    is Expense or Not
    """
    js = json.loads(txt)
    values = js.values()
    for value in values:
        tax = value[0]
        return int(tax) == 0


def get_expenses(tax):
    """
    Get Expenses from tax
    """
    items = []
    js = json.loads(tax.item_wise_tax_detail)
    values = js.values()
    for item in values:
        items.append({
            'account': tax.account_head,
            'amount': item[1],
        })
    return items


def getAccountNumber(account_name):
    """
    Get Account Number
    or None
    """
    if account_name:
        return frappe.get_value('Account', account_name, 'account_number')
    else:
        return None 


def docs(doc, start, end, exported=True):
    "Get Docs"

    filters = [
        ['posting_date', 'between', [start, end]],
        ['docstatus', '=', 1]
    ]

    if exported:
        filters.append(['exported_to_abacus', '=', 0])

    return frappe.get_list(doc, filters=filters)


def get_xml(content):
    """
    Create XML Response
    """
    resp = Response()
    resp.mimetype = 'text/xml'
    resp.charset = 'utf-8'
    resp.data = content
    return resp


def data(invoices, transactions, start_date, end_date, sales_invoice_no, purchase_invoice_no, payment_entry_no):
    """
    Build Data
    """
    return {
        'start_date': start_date,
        'end_date': end_date,
        'sales_invoice_no': sales_invoice_no,
        'purchase_invoice_no': purchase_invoice_no,
        'payment_entry_no': payment_entry_no,
        'invoices': invoices,
        'transactions': transactions
    }


def taxes(template, inv):
    """
    Taxes
    -----
    Get Taxes if Any
    """
    if inv.taxes_and_charges:
        tax_record = frappe.get_doc(template, inv.taxes_and_charges)
        tax_code = getattr(tax_record, 'tax_code', 312)
        rate = tax_record.taxes[0].rate
        taxAccount = tax_record.taxes[0].account_head
        taxAccountNumber = getAccountNumber(taxAccount)
    else:
        tax_code = None
        taxAccount = None
        rate = 0
        taxAccountNumber = None
    return [tax_code, taxAccount, rate, taxAccountNumber]


def rounding_off(inv):
    """
    Rounding Off Amount
    """
    if inv.rounding_adjustment:

        company = inv.company

        roundingAccount = frappe.get_doc(
            'Company', company).round_off_account

        return {
            'account':  getAccountNumber(roundingAccount),
            'amount': inv.rounding_adjustment,
            'keyamount': inv.base_rounding_adjustment,
            'currency': inv.currency,
            'tax_account':   None,
            'tax_amount': None,
            'tax_rate':  None,
            'tax_code': None,
            'tax_currency': None,
        }
    else:
        return None


def document_number(inv_name):
    """
    Converts
    ACC-PINV-2021-00003 => 202100003
    """
    split_inv_name = inv_name.split('-')
    join_inv_name = ''.join(split_inv_name)
    num = [i for i in join_inv_name if i.isdigit()]
    return ''.join(num)


def invoice(inv, account_name,  debit_credit, key_currency, tax_account):
    """
    For consistent Invoice
    """
    return {
        'account': getAccountNumber(account_name),
        'amount': round(inv.rounded_total - inv.write_off_amount, 2),
        'key_amount': round(inv.base_rounded_total - inv.base_write_off_amount, 2),
        'against_singles': [],
        'debit_credit': debit_credit,
        'date': inv.posting_date,
        'currency': inv.currency,
        'key_currency': key_currency,
        'exchange_rate': inv.conversion_rate,
        'text1': inv.name,
        'tax_account': tax_account,
        'document_number': document_number(inv.name)
    }


def amount(item, income_account, inv_currency,  taxAccount, rate, code, tax_currency):
    """
    Amount: for items
    """
    return {
        'account':  getAccountNumber(income_account),
        'amount': round(item.net_amount + (item.net_amount * rate / 100), 2),
        'keyamount': round(item.base_net_amount + (item.base_net_amount * rate / 100), 2),
        'currency': inv_currency,
        'tax_account':   getAccountNumber(taxAccount) if taxAccount else None,
        'tax_amount': item.base_net_amount * rate / 100,
        'tax_rate': rate or None,
        'tax_code': item.steuerziffer_ch if item.steuerziffer_ch != None else code,
        'tax_currency': tax_currency,
    }


def write_off(inv):
    return {
        'account':  getAccountNumber(inv.write_off_account),
        'amount': - round(inv.base_write_off_amount, 2),
        'keyamount': - round(inv.base_write_off_amount, 2),
        'currency': inv.currency,
        'tax_account':   None,
        'tax_amount': None,
        'tax_rate':  None,
        'tax_code':  "312",
        'tax_currency': inv.currency,
    }


def reset_docs(start_date, end_date):
    """
    Reset Docs Between Date Range
    """
    invoices = docs('Sales Invoice', start_date, end_date, False)
    purchaseInvoices = docs('Purchase Invoice', start_date, end_date, False)
    paymentEntry = docs('Payment Entry', start_date, end_date, False)

    reset_accounts('Sales Invoice', invoices, 0)
    reset_accounts('Purchase Invoice', purchaseInvoices, 0)
    reset_accounts('Payment Entry', paymentEntry, 0)


def reset_accounts(type, docs, flag):
    """
    Reset Document
    """
    for doc in docs:
        frappe.set_value(type, doc.name,  'exported_to_abacus', flag)


def payment_entry_amount(inv):
    total = 0
    total = total + inv.paid_amount

    for deduction in inv.deductions:
        total = total + deduction.amount

    return total
