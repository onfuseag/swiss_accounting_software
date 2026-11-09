frappe.ui.form.on("Bank Statement Import", {
	async custom_convert_xml_to_csv(frm) {
		if (!frm.doc.custom_camt_xml_file) {
			frappe.msgprint(__("Select a CAMT XML file first."));
			return;
		}

		if (frm.is_new()) {
			await frm.save();
		}

		const response = await frappe.call({
			method: "swiss_accounting_software.camt_erpnext.bank_statement_import.convert_xml_to_csv",
			args: {
				file: frm.doc.custom_camt_xml_file,
				data_import: frm.doc.name,
			},
			freeze: true,
			freeze_message: __("Converting CAMT XML"),
		});

		if (response.message) {
			await frm.set_value("import_file", response.message);
			await frm.save();
		}
	},
});
