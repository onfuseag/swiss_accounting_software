/*! *****************************************************************************
Licensed under the GPL, Version 3.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at https://www.gnu.org/licenses/gpl-3.0.en.html

THIS CODE IS PROVIDED ON AN *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
MERCHANTABLITY OR NON-INFRINGEMENT.

***************************************************************************** */
import { calculateQRReferenceChecksum } from "swissqrbill/utils"
import { FRAPPE_FILE_UPLOAD_ENDPOINT } from "./constant";
import { updateMessage } from "./message";

/**
 * Shows Progress Bar For Uploading QR Bill
 * @param {Number} current Current Progress
 * @param {String} description Desciption
 */
export const showProgress = (current, description) => {
  const title = updateMessage;
  const total = 100;
  window.frappe.show_progress(title, current, total, description, true);
};

/**
 * Creates Filename For Uploading File
 * @param {String} name Name of File
 * @returns String
 */
const _filename = (name) => `${name}-QR.pdf`;

/**
 * Frappe Upload File As Attachment to
 * Frappe Cloud
 * @param {Blob} file PDF File Blob
 * @param {String} docname Document Name
 * @param {Object} frm Frappe Form Object
 */
export const uploadFileAsAttachment = (file, docname, frm) => {
  const reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onloadend = function () {
    let formdata = new FormData();
    formdata.append("is_private", 1);
    formdata.append("folder", "Home/Attachments");
    formdata.append("doctype", "Sales Invoice");
    formdata.append("docname", docname);
    formdata.append("pdf_data", reader.result);
    fetch(FRAPPE_FILE_UPLOAD_ENDPOINT, {
      headers: {
        Accept: "application/json",
        "X-Frappe-CSRF-Token": window.frappe.csrf_token,
      },
      method: "POST",
      body: formdata,
    }).then(() => {
      showProgress(100, "done");
      frm.reload_doc();
    });
  };
};

/**
 * Shows Error Alert
 * @param {String} error Error Message
 */
export const showError = (error) => {
  window.frappe.hide_progress();
  window.frappe.throw(error + "");
};

/**
 * Download File Name
 * @param {URL} uri URL to Set For Virtual Button
 * @param {String} filename File Name of Download
 */
export const triggerDownload = (uri, filename) => {
  var evt = new MouseEvent("click", {
    view: window,
    bubbles: false,
    cancelable: true,
  });
  var a = document.createElement("a");
  a.setAttribute("download", filename);
  a.setAttribute("href", uri);
  a.setAttribute("target", "_blank");
  a.dispatchEvent(evt);
};

/**
 * Returns Language Code For Swiss QR Bill
 * @param {String} language Language
 * @returns {String} Returns Language Code For Download
 */
export const getLanguageCode = (language) => {
  if (language === "en-US" || language === "en-GB") {
    return "EN";
  }

  if (
    (language === "en") |
    (language === "fr") |
    (language === "it") |
    (language === "de")
  ) {
    return language.toUpperCase();
  }
  return "DE";
};

/**
 *
 * @param {String} doctype Doctype
 * @param {String} docname Docname
 * @param {String} error Error Message
 * @returns {Promise} Doc
 */
export const getDocument = async (doctype, docname) => {
  try {
    return await window.frappe.db.get_doc(doctype, docname);
  } catch (error) {
    showError(error);
  }
};

/**
 * Calculates and Returns Reference Code
 * @param {String} docname DocumentName
 * @returns {String} Reference Code
 */
export const getReferenceCode = (docname) => {
  const _ref = docname.split("-").join("");
  const ref = _ref.substr(_ref.length - 7);
  const _reference = `000000000000000000${ref}0`;
  const checksum = calculateQRReferenceChecksum(_reference);
  return `${_reference}${checksum}`;
};

/**
 * Returns Currency Code or Shows Error
 * @param {String 'CHF' | 'EUR'} currency Currency
 * @returns Currency Code
 * @throws {Error} Currency Should Either Be CHF or EUR
 */
export const getCurrency = (currency) => {
  if (currency === "CHF" || currency === "EUR") {
    return currency;
  }
  showError("Currency Should Be Either CHF or EUR");
};
