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
import blobStream from "blob-stream";
import { SwissQRBill } from "swissqrbill/pdf";
import { showError, showProgress, uploadFileAsAttachment } from "./utils";

export const generateQRPDF = (paymentinfo, docname, frm, papersize, language) => {
  try {
    const stream = new BlobStream();
    const pdf = new PDFDocument();
    const qrBill = new SwissQRBill(paymentinfo);

    qrBill.attachTo(pdf);

    // Show progress while generating
    showProgress(60, "generating pdf...");

    
    stream.on("finish", () => {
      showProgress(80, "uploading pdf...");

      
      const blob = stream.toBlob("application/pdf");

      uploadFileAsAttachment(blob, docname, frm);
    });
  } catch (error) {
    showError(error);
  }
};

/*
export const generateQRPDF = (
  paymentinfo,
  docname,
  frm,
  papersize,
  language
) => {
  const data = paymentinfo;
  const stream = new SwissQRBill.BlobStream();
  try {
    const pdf = new SwissQRBill.PDF(data, stream, {
      language: language || "DE",
      size: papersize || "A6/5",
    });
    showProgress(60, "generating pdf...");
    pdf.on("finish", () => {
      // const url = stream.toBlobURL("application/pdf");
      // const triggerDownload()
      showProgress(80, "uploading pdf...");
      uploadFileAsAttachment(stream.toBlob(), docname, frm);
    });
  } catch (error) {
    showError(error);
  }
};
*/