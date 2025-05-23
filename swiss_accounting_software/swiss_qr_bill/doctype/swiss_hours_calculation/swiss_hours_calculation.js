// Copyright (c) 2025, ONFUSE AG and contributors
// For license information, please see license.txt


frappe.ui.form.on("Swiss Hours Calculation", {
    refresh(frm) {
        

        frm.add_custom_button("Recalculate", () => {
            if (frm.doc.docstatus === 1) {
                frappe.msgprint({
                    title: __("Not Allowed"),
                    message: __("This document is already submitted and cannot be changed."),
                    indicator: "red"
                });
                return;
            }
            frm.set_value("status", "Open");
            frm.save();
        });
    }
});