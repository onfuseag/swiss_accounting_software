
// For license information, please see license.txt

frappe.ui.form.on("Swiss QR Bill Settings", {
	refresh(frm) {
		set_qr_code_type_description(frm);
	},
	qr_code_type(frm) {
		set_qr_code_type_description(frm);
	},
});

function set_qr_code_type_description(frm) {
	const descriptions = {
		QRR: __("27-digit QR reference. Requires a QR-IBAN."),
		SCOR: __("Creditor reference (ISO 11649, RF…). Requires a regular IBAN."),
		NON: __("No payment reference. Requires a regular IBAN."),
	};
	const selected = frm.doc.qr_code_type;
	const description = Object.entries(descriptions)
		.map(([type, text]) => {
			const line = `<b>${type}</b>: ${text}`;
			return type === selected ? line : `<span class="text-muted">${line}</span>`;
		})
		.join("<br>");
	frm.set_df_property("qr_code_type", "description", description);
}
