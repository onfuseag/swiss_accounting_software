// Copyright (c) 2025, ONFUSE AG and contributors
// For license information, please see license.txt


frappe.ui.form.on("Swiss Hours Calculation", {
    refresh(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch last submitted hours"), async () => {
                if (frm.doc.docstatus !== 0) {
                    return;
                }

                if (!frm.doc.employee || !frm.doc.from_date) {
                    frappe.msgprint(__("Select an employee and From Date before fetching previous hours."));
                    return;
                }

                const employee = frm.doc.employee;
                const fromDate = frm.doc.from_date;
                const records = await frappe.db.get_list("Swiss Hours Calculation", {
                    filters: {
                        employee,
                        docstatus: 1,
                        to_date: ["<", fromDate],
                    },
                    fields: ["new_balance"],
                    order_by: "to_date desc, creation desc",
                    limit: 1,
                });

                if (
                    frm.doc.docstatus !== 0 ||
                    frm.doc.employee !== employee ||
                    frm.doc.from_date !== fromDate
                ) {
                    return;
                }

                if (!records?.length) {
                    frappe.msgprint(__("No earlier submitted hours calculation was found for this employee."));
                    return;
                }

                await frm.set_value("previous_hours", records[0].new_balance || 0);
            });
        }

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
