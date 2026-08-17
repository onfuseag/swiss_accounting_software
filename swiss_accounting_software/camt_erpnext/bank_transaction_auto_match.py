import frappe
from frappe.desk.form.assign_to import add
from frappe.utils import flt


@frappe.whitelist()
def bank_transaction_auto_match(doc, event=None):
	if doc.status != "Unreconciled":
		return

	if _try_match_sales_invoice(doc):
		return

	_assign_unreconciled(doc)


def _try_match_sales_invoice(doc):
	reference = _normalize_esr(doc.reference_number)
	if len(reference) <= 10:
		return False

	if not flt(doc.deposit):
		return False

	invoices = frappe.get_all(
		"Sales Invoice",
		fields=["name", "outstanding_amount", "customer", "debit_to", "currency"],
		filters={
			"esr_reference_code": reference,
			"docstatus": 1,
			"status": ["!=", "Cancelled"],
			"outstanding_amount": [">", 0],
		},
	)
	if not invoices:
		invoices = frappe.get_all(
			"Sales Invoice",
			fields=["name", "outstanding_amount", "customer", "debit_to", "currency"],
			filters={
				"esr_reference_code": doc.reference_number,
				"docstatus": 1,
				"status": ["!=", "Cancelled"],
				"outstanding_amount": [">", 0],
			},
		)

	threshold = flt(frappe.db.get_value("Swiss QR Bill Settings", doc.company, "threshold_payment_difference"))

	for inv in invoices:
		if doc.currency != inv.currency:
			continue

		match = _get_allocation(inv, flt(doc.deposit), threshold)
		if not match:
			continue

		if _create_and_link_payment(doc, inv, match):
			return True

	return False


def _get_allocation(inv, deposit, threshold):
	outstanding = flt(inv.outstanding_amount)
	difference = outstanding - deposit

	# Full remaining balance (small difference can be written off)
	if abs(difference) <= threshold:
		return {
			"allocated_amount": outstanding,
			"write_off": difference if difference else 0,
			"payment_term": None,
			"payment_term_outstanding": None,
		}

	# Overpayment beyond threshold: do not auto-match
	if deposit > outstanding + threshold:
		return None

	# Partial payment: prefer a matching payment term, otherwise allocate the deposit
	term = _find_matching_payment_term(inv.name, deposit, threshold)
	if term:
		term_outstanding = flt(term.outstanding or term.payment_amount)
		return {
			"allocated_amount": term_outstanding,
			"write_off": term_outstanding - deposit if abs(term_outstanding - deposit) > 0 else 0,
			"payment_term": term.payment_term,
			"payment_term_outstanding": term_outstanding,
		}

	return {
		"allocated_amount": deposit,
		"write_off": 0,
		"payment_term": None,
		"payment_term_outstanding": None,
	}


def _find_matching_payment_term(invoice_name, deposit, threshold):
	rows = frappe.get_all(
		"Payment Schedule",
		filters={"parent": invoice_name, "parenttype": "Sales Invoice"},
		fields=["name", "payment_term", "outstanding", "payment_amount", "due_date", "idx"],
		order_by="idx asc",
	)
	for row in rows:
		term_outstanding = flt(row.outstanding if row.outstanding else row.payment_amount)
		if term_outstanding > 0 and abs(term_outstanding - deposit) <= threshold:
			return row
	return None


def _create_and_link_payment(doc, inv, match):
	paid_to = frappe.db.get_value("Bank Account", doc.bank_account, "account")
	allocated = flt(match["allocated_amount"])
	write_off = flt(match["write_off"])

	deduction_entry = []
	if write_off:
		comp = frappe.db.get_value("Company", doc.company, ["write_off_account", "cost_center"], as_dict=1)
		if comp and comp.write_off_account:
			deduction_entry = [
				{
					"account": comp.write_off_account,
					"cost_center": comp.cost_center,
					"amount": write_off,
				}
			]

	reference = {
		"reference_doctype": "Sales Invoice",
		"reference_name": inv.name,
		"allocated_amount": allocated,
		"outstanding_amount": flt(inv.outstanding_amount),
	}
	if match.get("payment_term"):
		reference["payment_term"] = match["payment_term"]
		reference["payment_term_outstanding"] = match.get("payment_term_outstanding")

	acc_pay = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"party_type": "Customer",
			"company": doc.company,
			"party": inv.customer,
			"payment_type": "Receive",
			"bank_account": doc.bank_account,
			"paid_to": paid_to,
			"paid_from": inv.debit_to,
			"paid_amount": flt(doc.deposit),
			"paid_from_account_currency": doc.currency,
			"paid_to_account_currency": doc.currency,
			"posting_date": doc.date,
			"received_amount": flt(doc.deposit),
			"source_exchange_rate": 1.0,
			"target_exchange_rate": 1.0,
			"reference_no": _normalize_esr(doc.reference_number) or doc.reference_number,
			"reference_date": doc.date,
			"deductions": deduction_entry,
			"references": [reference],
		}
	)
	acc_pay.insert(ignore_permissions=True)
	acc_pay.submit()

	if not acc_pay.name:
		return False

	doc.append(
		"payment_entries",
		{
			"payment_document": "Payment Entry",
			"payment_entry": acc_pay.name,
			"allocated_amount": flt(doc.deposit),
		},
	)
	doc.save(ignore_permissions=True)
	return True


def _assign_unreconciled(doc):
	doc.reload()
	if doc.status != "Unreconciled":
		return

	assign_unreconciled_transactions_to = frappe.db.get_value(
		"Swiss QR Bill Settings", doc.company, "assign_unreconciled_transactions_to"
	)
	if not assign_unreconciled_transactions_to:
		return

	add(
		{
			"assign_to": [assign_unreconciled_transactions_to],
			"doctype": "Bank Transaction",
			"name": doc.name,
			"description": "Unreconciled Payment",
		},
		ignore_permissions=True,
	)


def _normalize_esr(reference):
	if not reference:
		return ""
	return str(reference).replace(" ", "").strip()
