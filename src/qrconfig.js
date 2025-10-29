/*! *****************************************************************************
Licensed under the GPL, Version 3.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at https://www.gnu.org/licenses/gpl-3.0.en.html

THIS CODE IS PROVIDED ON AN *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
MERCHANTABLITY OR NON-INFRINGEMENT.

***************************************************************************** */

/**
 * Creates Address Configuration
 * @param {String} currency CHF | EUR
 * @param {*} amount Amount To Pay
 * @param {String} reference Reference Code
 * @param {String} company Company Name
 * @param {Object} companyAddress Company Address
 * @param {String} companyAddressCode ALPHA-2 Address Code
 * @param {String} iban QR-IBAN
 * @param {String} customer Customer Name, max 70 Chars, rest will be removed
 * @param {Object} customerAddress Customer Address, max 70 Chars, rest will be removed
 * @param {String} customerAddressCode Customer Address Code
 * @returns Address Configuration
 */
export const generateQRConfig = (
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
) => ({
  currency,
  amount,
  reference,
  creditor: {
    name: company, //
    address: companyAddress.address_line1.substring(0, 70),
    buildingNumber: companyAddress.address_line2 != null ? companyAddress.address_line2.substring(0,16) : undefined, // Optional Address line2, according to Type "S" specification
    zip: parseInt(companyAddress.pincode), // Bank Account  Code
    city: companyAddress.city, // Bank Account City
    account: iban, // Bank Account Iban
    country: companyAddressCode, // Bank Country
  },
  debtor: {
    name: customer.substring(0, 70), // Customer Doctype,
    address: customerAddress.address_line1.substring(0, 70),
    buildingNumber: customerAddress.address_line2 != null ? customerAddress.address_line2.substring(0,16) : undefined, // Optional Address line2, according to Type "S" specification
    zip: customerAddress.pincode, // Sales Invoice PCode
    city: customerAddress.city, // Sales Invoice City
    country: customerAddressCode, // Sales Invoice Country
  },
});
