frappe.ui.form.on("Sales Invoice", {
	onload(frm) {
		if (frm.doc.docstatus == 1) {
			return;
		}
		frm.doc.esr_reference_code = "";
	},

	refresh(frm) {
		frm.add_custom_button("Create QR Bill", () => createQRBill(frm));
	},
});

function createQRBill(frm) {
	frappe.show_progress(__("Uploading QR Bill"), 40, 100, __("generating pdf..."), true);
	frappe.call({
		method: "swiss_accounting_software.attach_pdf.attach_pdf",
		args: { docname: frm.doc.name },
		freeze: true,
		freeze_message: __("Generating QR Bill"),
		callback() {
			frappe.show_progress(__("Uploading QR Bill"), 100, 100, __("done"), true);
			frappe.hide_progress();
			frm.reload_doc();
		},
		error() {
			frappe.hide_progress();
		},
	});
}
