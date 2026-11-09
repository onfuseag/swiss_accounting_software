# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _


def check_app_permission():
	"""Show the app when its module is visible and a linked DocType is readable."""
	from frappe.utils.modules import is_module_visible

	return is_module_visible("Swiss QR Bill") and any(
		frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, "read")
		for doctype in (
			"Swiss Hours Calculation",
			"Swiss Calculation Settings",
			"Steuerziffer CH",
			"Swiss QR Bill Settings",
			"Bank Statement Import",
			"Bank Transaction",
			"Attendance",
			"Employee Checkin",
			"Shift Type",
			"Shift Assignment",
			"Leave Application",
			"Leave Allocation",
			"Timesheet",
		)
	)


def get_data():
	return [
		{
			"module_name": "Swiss Accounting Software",
			"color": "grey",
			"icon": "octicon octicon-file-directory",
			"type": "module",
			"label": _("Swiss Accounting Software")
		}
	]
