/*! *****************************************************************************
Licensed under the GPL, Version 3.0 (the "License"); you may not use
this file except in compliance with the License. You may obtain a copy of the
License at https://www.gnu.org/licenses/gpl-3.0.en.html

THIS CODE IS PROVIDED ON AN *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
MERCHANTABLITY OR NON-INFRINGEMENT.

***************************************************************************** */

import PDFDocument from "pdfkit/js/pdfkit.standalone.js";
import { SwissQRBill } from "swissqrbill/pdf";
import { showError, showProgress, uploadFileAsAttachment } from "./utils";

export const generateQRPDF = (paymentinfo, docname, frm, language) => {

  try {
    showProgress(10, "initializing pdf...");

    const pdf = new PDFDocument();
    const chunks = [];

    // Collect bytes directly from pdfkit
    pdf.on("data", (d) => chunks.push(d));
    pdf.on("error", showError);

    
    pdf.on("end", () => {

      showProgress(80, "uploading pdf...");
      // Create a Blob from the chunks
      const blob = new Blob(chunks, { type: "application/pdf" });
      uploadFileAsAttachment(blob, docname, frm);

    });

    // Attach the Swiss QR bill
    const qrBill = new SwissQRBill(paymentinfo);
    qrBill.attachTo(pdf);

    showProgress(60, "generating pdf...");
    
    pdf.end(); // finalize    

  } catch (error) {
    showError(error);
  }
};
