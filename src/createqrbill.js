/*! *****************************************************************************
Licensed under the GPL, Version 3.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at https://www.gnu.org/licenses/gpl-3.0.en.html

THIS CODE IS PROVIDED ON AN *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
MERCHANTABLITY OR NON-INFRINGEMENT.

***************************************************************************** */
import { generateQRPDF } from "./generateqrpdf";
import { generateQRConfig } from "./qrconfig";
import {
  getCurrency,
  getDocument,
  getLanguageCode,
  getReferenceCode,
  showError,
  showProgress,
} from "./utils";

export const createQRBill = async (frm) => {
  showProgress(10, "getting data...");
  var customer = ""

  // If customer name exists separately
  if (!frm.doc.customer_name) {
    customer = frm.doc.customer
  } else {
    customer = frm.doc.customer_name
  }

  const amount = frm.doc.outstanding_amount;
  const reference = getReferenceCode(frm.doc.name);
  const company = frm.doc.company;
  const language = getLanguageCode(frm.doc.language);
  const bank = await getDocument("Swiss QR Bill Settings", company);
  const bankAccount = bank.bank_account;
  const currency = getCurrency(frm.doc.currency);
  if (!currency) return;

  const companyAddress = await getDocument("Address", frm.doc.company_address);
  const customerAddress = await getDocument(
    "Address",
    frm.doc.customer_address
  );
  const { iban } = await getDocument("Bank Account", bankAccount);

  showProgress(40, "generating pdf...");

  const companyCountry = await getDocument("Country", companyAddress.country);
  const customerCountry = await getDocument("Country", customerAddress.country);

  const companyAddressCode = companyCountry.code.toUpperCase();
  const customerAddressCode = customerCountry.code.toUpperCase();

  const config = generateQRConfig(
    currency,
    amount,
    company,
    companyAddress,
    companyAddressCode,
    iban,
    customer,
    customerAddress,
    customerAddressCode,
    reference
  );

  generateQRPDF(config, frm.docname, frm, "A4", language);
};
