import frappe

from frappe.desk.form.assign_to import add

@frappe.whitelist()
def bank_transaction_auto_match(doc, event=None): 
    
    # Only do this for Unreconciled docs
    if doc.status == "Unreconciled": 

        # Check that it has a reference number
        if doc.reference_number is not None:
            
            # Make sure this has a ref number
            if len(doc.reference_number) > 10: 
                
                # Fetch the holidays in the holiday list for the current year
                invoices = frappe.get_all('Sales Invoice', fields=['name','outstanding_amount','customer', 'debit_to', 'currency'], filters={
                    'esr_reference_code': doc.reference_number
                })
                
                # Correct invoice found, trying to reconcile
                if invoices is not None: 
                    
                    # Get the payment difference default from storage
                    threshold = frappe.db.get_value("Swiss QR Bill Settings", doc.company, "threshold_payment_difference")
                    
                    # Loop through invoices and create list
                    for inv in invoices: 
                        
                        # Make sure the currencies match up, so we can do a transaction 1:1
                        if (doc.currency == inv.currency):
                            
                            
                            if abs(inv.outstanding_amount - doc.deposit) <= threshold:
                                
                                deduction_entry = []
                                
                                if abs(inv.outstanding_amount-doc.deposit) > 0:
                                    
                                    comp = frappe.db.get_value('Company', doc.company, ['write_off_account', 'cost_center'], as_dict=1)
                                    deduction_entry = [{
                                        "account": comp.write_off_account, 
                                        "cost_center": comp.cost_center,
                                        "amount": inv.outstanding_amount-doc.deposit #Without abs!
                                    }]
                                
                                paid_to = frappe.db.get_value('Bank Account', doc.bank_account, 'account')
                                
                                
                                # Create the payment entry
                                acc_pay = frappe.get_doc({
                                    "doctype": "Payment Entry", 
                                    "party_type" : "Customer",
                                    "company": doc.company,
                                    "party" : inv.customer,
                                    "payment_type": "Receive", 
                                    "bank_account" : doc.bank_account,
                                    "paid_to": paid_to,
                                    "paid_from": inv.debit_to,
                                    "paid_amount": doc.deposit,
                                    "paid_from_account_currency": doc.currency,
                                    "paid_to_account_currency": doc.currency,
                                    "posting_date": doc.date,
                                    "received_amount": doc.deposit,
                                    "target_exchange_rate" : 1.0, # Only domestic
                                    "reference_no": doc.reference_number, 
                                    "reference_date": doc.date,
                                    "deductions": deduction_entry,
                                    "docstatus": 1, # Submit this document automatically
                                    "references": [{
                                        "reference_doctype" : "Sales Invoice", 
                                        "reference_name" : inv.name, 
                                        "allocated_amount" : inv.outstanding_amount
                                    }]
                                })
                                
                                acc_pay.insert(ignore_permissions=True)
                                
                                if acc_pay.name:
                                    child = frappe.new_doc("Bank Transaction Payments")
                                    
                                    # Update the current doctype to inform it has been inserted
                                    doc.append('payment_entries',{
                                        "payment_document": "Payment Entry", 
                                        "payment_entry" : acc_pay.name, 
                                        "allocated_amount" : doc.deposit # Make sure to allocate the full amount
                                    })
                                    
                                    doc.save(ignore_permissions=True)

                                    return
    
    # Reload and see if the doc has been changed to reconciled
    doc.reload()

    # If the Payment is unreconciled, we get the user from swiss qr Bill settings and assign it to the dataset
    if doc.status == "Unreconciled": 
        assign_unreconciled_transactions_to = frappe.db.get_value("Swiss QR Bill Settings", doc.company, "assign_unreconciled_transactions_to")

        if assign_unreconciled_transactions_to:
            args = {
                "assign_to": [assign_unreconciled_transactions_to],
                "doctype": "Bank Transaction",
                "name": doc.name,
                "description": "Unreconciled Payment",
            }

            add(args, ignore_permissions=True)