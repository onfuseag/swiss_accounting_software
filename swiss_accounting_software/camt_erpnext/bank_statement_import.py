import frappe
import csv
import json
import os
import datetime
from datetime import datetime
from pytz import timezone
import re
import xml.etree.ElementTree as ET

def remove_namespaces(xml_file):
    # Parse the XML from a file path directly
    it = ET.iterparse(xml_file, events=('start',))
    for _, el in it:
        # Remove namespace from the element tag if present
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return it.root

@frappe.whitelist()
def convert_xml_to_csv(file):

    xml_file = get_absolute_path(file) #getting file with path

    current_date= datetime.now()
    current_datetime = current_date.strftime("%d-%m-%Y %H:%M:%S")

    filename = f'{frappe.utils.get_bench_path()}/sites/{frappe.utils.get_site_base_path()[2:]}/public/files/{current_datetime}.csv'
    
    # Parse the XML and remove namespace
    root = remove_namespaces(xml_file)

    with open(filename, "w", newline='') as csvfile:

        csv_writer = csv.writer(csvfile)

        # Write the top section to the csv
        headers = ['Date','Bank Account','Company','Deposit','Withdrawal','Reference Number','Description']
        csv_writer.writerow(headers)

        # Iterate through each Ntry (entry) element in the XML
        for ntry in root.findall('.//Ntfctn/Ntry'):

            # Extract common data for all transactions in this entry
            date = ntry.find('.//BookgDt/Dt').text
            bank_account = root.find('.//Acct/Id/IBAN').text
            
            # Transactions could be multiple; iterate through each TxDtls (Transaction Details)
            for tx in ntry.findall('.//TxDtls'):
                # Initialize a description string
                description = f"Payment from {tx.find('.//Dbtr/Pty/Nm').text if tx.find('.//Dbtr/Pty/Nm') is not None else 'Unknown'}"
                amt = tx.find('.//Amt').text
                cdt_dbt_ind = tx.find('.//CdtDbtInd').text
                reference = tx.find('.//CdtrRefInf/Ref').text
                
                # Set the variables beforehand
                deposit = ""
                withdrawal = ""

                # Check if it is a deposit or a withdrawal
                if (cdt_dbt_ind == 'CRDT'):
                    deposit = amt
                else: 
                    withdrawal = amt
                
                # Append the extracted information to the records list
                csv_writer.writerow([date,bank_account,'',deposit,withdrawal,reference,description])
    
    return filename

#@frappe.whitelist()
def get_absolute_path(file_name):
	if(file_name.startswith('/files/')):
		file_path = f'{frappe.utils.get_bench_path()}/sites/{frappe.utils.get_site_base_path()[2:]}/public{file_name}'
	if(file_name.startswith('/private/')):
		file_path = f'{frappe.utils.get_bench_path()}/sites/{frappe.utils.get_site_base_path()[2:]}{file_name}'
	return file_path