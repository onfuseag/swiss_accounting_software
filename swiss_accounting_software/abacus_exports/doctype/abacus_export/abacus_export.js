// For license information, please see license.txt

const FRAPPE_FILE_UPLOAD_ENDPOINT = "/api/method/upload_file";

frappe.ui.form.on("Abacus Export", {
  refresh: (frm) => {
    if (frm.doc.docstatus == 1) {
      frm.add_custom_button("Re Export", function () {
        const { start_date, end_date, company } = frm.doc;
        const { doctype, docname } = frm;

        showProgress(20, "Getting File", "Getting File");

        fetch(
          encodeURI(
            `/api/method/swiss_accounting_software.reset_account?start_date=${start_date}&end_date=${end_date}&company=${company}&doctype=${doctype}&docname=${docname}`
          )
        )
          .then((data) => data.json())
          .then((data) => data.message.file)
          .then((file) => attachFile(doctype, docname, file, frm))
          .catch((err) => {
            window.frappe.hide_progress();
            window.frappe.throw(err + "");
          });
      });
    }
  },
});

const showProgress = (current, description) => {
  const title = "Recreating XML";
  const total = 100;
  window.frappe.show_progress(title, current, total, description, true);
};

const attachFile = (doctype, docname, file, frm) => {
  let formData = new FormData();
  formData.append("is_private", 1);
  formData.append("folder", "Home/Attachments");
  formData.append("doctype", doctype);
  formData.append("docname", docname);
  formData.append("file", new Blob([file], { type: "text/xml" }), "abacus.xml");

  showProgress(60, "Uploading File", "Uploading File");
  fetch(FRAPPE_FILE_UPLOAD_ENDPOINT, {
    headers: {
      Accept: "application/json",
      "X-Frappe-CSRF-Token": window.frappe.csrf_token,
    },
    method: "POST",
    body: formData,
  }).then(() => {
    showProgress(100, "done", "done");
    frm.reload_doc();
  });
};
