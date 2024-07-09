# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "swiss_accounting_software"
app_title = "Swiss Accounting Integration"
app_publisher = "ONFUSE AG"
app_description = "ERPNexts functionality with Swiss QR Integration and payment automation"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "contact@onfuse.ch"
app_license = "MIT"
fixtures = [
    {"dt": "Custom Field", "filters": [["fieldname", "in", ("esr_reference_code", 'tax_code', 'exported_to_abacus')]]}, 
    {"doctype": "Custom Field", "filters": [["dt", "=", "Bank Statement Import"]]}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/swiss_accounting_software/css/swiss_accounting_software.css"
# app_include_js = "/assets/swiss_accounting_software/js/swiss_accounting_software.js"
app_include_js = "/assets/swiss_accounting_software/js/index.js"

# include js in doctype views
doctype_js = {"Bank Statement Import" : "public/js/bank_statement_import.js"}

# include js, css files in header of web template
# web_include_css = "/assets/swiss_accounting_software/css/swiss_accounting_software.css"
# web_include_js = "/assets/swiss_accounting_software/js/swiss_accounting_software.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "swiss_accounting_software/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "swiss_accounting_software.install.before_install"
# after_install = "swiss_accounting_software.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "swiss_accounting_software.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Abacus Export": {
        "on_submit": "swiss_accounting_software.attach_xml",
    }, 
    "Bank Transaction": {
        "on_submit": "swiss_accounting_software.camt_erpnext.bank_transaction_auto_match.bank_transaction_auto_match"
    },
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"swiss_accounting_software.tasks.all"
# 	],
# 	"daily": [
# 		"swiss_accounting_software.tasks.daily"
# 	],
# 	"hourly": [
# 		"swiss_accounting_software.tasks.hourly"
# 	],
# 	"weekly": [
# 		"swiss_accounting_software.tasks.weekly"
# 	]
# 	"monthly": [
# 		"swiss_accounting_software.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "swiss_accounting_software.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "swiss_accounting_software.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "swiss_accounting_software.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]
