# Copyright (c) 2025, ONFUSE AG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime
from dateutil.relativedelta import relativedelta

class SwissHoursCalculation(Document):
	
	def validate(self):
		if self.status == "Open":
			# Start the recalculation
			calculate_hours_for_employee(self)
		
		# Compute the totals in the additional table
		for row in self.additional:
			row.total = row.quantity * row.amount

	pass

# Function for filling out a dataset
def calculate_hours_for_employee(doc):

	# Security checks
	# If the employee has entered the company in the same month, make from date to the entry date
	date_of_joining = frappe.utils.getdate(doc.date_of_joining)
	from_date = frappe.utils.getdate(doc.from_date)
	to_date = frappe.utils.getdate(doc.to_date)

	# Start is before the current period
	if date_of_joining > to_date:
		doc.status = "Failed"
		return

	if date_of_joining > from_date: 
		doc.from_date = date_of_joining

	# Make sure the employee hasnt already left the company
	if doc.relieving_date:
		rel = frappe.utils.getdate(doc.relieving_date)
		if rel < from_date: 
			doc.status = "Failed"
			return
		
		# if the employee leaves during the period, we need to adjust the calculation
		if rel < to_date:
			doc.to_date = rel


	hr_settings = frappe.get_single("HR Settings")

	# We count this while going
	allowance = 0.0

	# Clear the old data from the document
	doc.leaves.clear()
	doc.timesheets.clear()

	# STEP 1: Get the settings for the user
	calculation_settings = frappe.db.get_all(
		"Swiss Calculation Settings",
		filters={
			"enabled": 1,
			"employment_type": doc.employment_type
		},
		fields=["name"]
	)

	if not calculation_settings: 
		return

	calculation_setting = frappe.get_doc("Swiss Calculation Settings", calculation_settings[0]["name"])


	# STEP 2: Get Company or Employee holidays
	holiday_list, company = frappe.db.get_value("Employee", doc.employee, ["holiday_list", "company"]) 
	holiday_days = 0
	
	if holiday_list is None:
		holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")

	if holiday_list is not None:
		holiday_days = get_holidays(holiday_list, doc.from_date, doc.to_date)


	# STEP 3: Get the total hours minus holidays (if any)
	total_days_between = frappe.utils.date_diff(doc.to_date, doc.from_date) + 1
	
	required_work_days = total_days_between - holiday_days
	

	# STEP 4: Get the working hours per day
	required_work_hours = 0.0
	required_work_hours_total = 0.0 # for the period

	if calculation_setting.working_hours != 0.0: # User did not define, best to use the company default
		required_work_hours = calculation_setting.working_hours
		required_work_hours_total = required_work_days * calculation_setting.working_hours
	else: 
		required_work_hours = hr_settings.standard_working_hours
		required_work_hours_total = required_work_days * hr_settings.standard_working_hours
	

	# STEP 5: Get the attendance
	attendance_records = frappe.get_all(
		"Attendance",
		filters={
			"employee" : doc.employee, 
			"attendance_date" : ["between", [doc.from_date, doc.to_date]], 
			"docstatus": ["not in", [0,2]], # Not cancelled or draft
		}, 
		fields=["name","working_hours", "status", "leave_type"],
	)

	# Check for the allowance
	for att in attendance_records:
		if att.status == "Present":
			allowance = allowance + get_allowance_for_day(calculation_setting, att.working_hours)
	
	
	# STEP 6, sort hours and add them up
	worked_hours = 0.0
	worked_hours = get_hours_from_attendance(attendance_records, required_work_hours, calculation_setting.count_leaves)

	# STEP 7, Get all timesheets, sort by activity and optionally add them to worked_hours
	tsdata = get_timesheet_data(doc.employee, doc.from_date, doc.to_date)

	# Go though the activities, if there is attendance tracking enabled, count it to working hours
	for tsa in tsdata:
		tsa.count_as_attendance = 0
		for setting in calculation_setting.timesheet_activities:
			if tsa.activity_type == setting.activity_type: 
				if setting.count_as_attendance == 1: 
					tsa.count_as_attendance = 1
					worked_hours = worked_hours + tsa.hours



		# Append it in the document table
		doc.append("timesheets", {
			"activity_type": tsa.activity_type,
			"count_as_attendance": tsa.count_as_attendance, 
			"hours": tsa.hours
		})

	# Calculate the new allowance for the timesheets as we have to do this daily
	allowance = allowance + get_timesheet_allowance_daily(doc.employee, doc.from_date, doc.to_date, calculation_setting)

	# STEP 8, Get leaves from HRMS
	leaves = get_leave_allocation_summary_attendance_based(doc.from_date, doc.to_date, doc.employee)
	for lv in leaves: 
		# Append it in the document table
		doc.append("leaves", {
			"leave_type": lv["leave_type"],
			"opening_balance": lv["opening_balance"], 
			"new_allocations": lv["new_allocations"],
			"leaves_taken": lv["consumed_leaves"], 
			"closing_balance": lv["closing_balance"]
		})

	# FINAL STEP: Set the new data

	# Add the monthly allowance, if there is any
	allowance = allowance + calculation_setting.monthly_allowance

	# Set the allowance in the table, if not already there
	found = False
	for row in doc.additional:
		if row.description == "Allowance":
			row.amount = allowance 
			row.quantity = 1
			row.total = allowance
			found = True
			break

	if not found:
		doc.append("additional", {
			"description": "Allowance",
			"amount": allowance,
			"quantity": 1,
			"total" : allowance
		})
	
	
	doc.required_hours = required_work_hours_total
	
	doc.worked_hours = worked_hours

	# Dont need the new balance if the setting forbids it
	if calculation_setting.count_balance == 0:
		doc.new_balance = 0.0
	else: 
		doc.new_balance = doc.previous_hours + worked_hours - required_work_hours_total

	# Finally set the calculation status to done
	doc.status = "Done"

# Get the daily allowance in a month for the timesheet
def get_timesheet_allowance_daily(employee, from_date, to_date, calculation_setting) -> float:
	allowance = 0.0

	conditions = [
		"employee = %(employee)s",
		"docstatus = 1"  # Submitted only
	]
	filters = {"employee": employee}

	if from_date:
		conditions.append("start_date >= %(from_date)s")
		filters["from_date"] = frappe.utils.getdate(from_date)
	if to_date:
		conditions.append("end_date <= %(to_date)s")
		filters["to_date"] = frappe.utils.getdate(to_date)

	where_clause = " AND ".join(conditions)

	# SQL query: Sum total_hours by date
	data = frappe.db.sql(f"""
		SELECT
			start_date,
			SUM(total_hours) AS hours
		FROM
			`tabTimesheet`
		WHERE {where_clause}
		GROUP BY
			start_date
		ORDER BY
			start_date
	""", filters, as_dict=True)

	for row in data:
		allowance = allowance + get_allowance_for_day(calculation_setting, row["hours"])

	return allowance

# helper function for getting allowance, returns amount in float
def get_allowance_for_day(calculation_setting, hours) -> float: 
	allowance = 0.0
	if calculation_setting.hourly_allowance != 0.0:
		allowance = (calculation_setting.hourly_allowance * hours)
	
	if calculation_setting.daily_allowance != 0.0 and calculation_setting.daily_allowance_after_hours != 0.0:
		# Only give this if the user worked more
		if hours > calculation_setting.daily_allowance_after_hours:
			allowance = calculation_setting.daily_allowance


	if allowance > calculation_setting.max_allowance_per_day:
		allowance = calculation_setting.max_allowance_per_day 

	return allowance

# ──────────────────────────────────────────────────────────────────────────────
# Helper functions, for counting the leave balance
# ──────────────────────────────────────────────────────────────────────────────
def _allocated_on(employee: str, leave_type: str, as_on: str) -> float:
	"""
	Sum of *approved* Leave Allocation units that cover `as_on` date.
	"""
	rows = frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"leave_type": leave_type,
			"docstatus": 1,			 # submitted only
			"from_date": ("<=", as_on),
			"to_date":   (">=", as_on),
		},
		pluck="total_leaves_allocated",
	)
	return sum(rows) if rows else 0.0


def _leaves_taken(employee: str, leave_type: str, from_date: str, to_date: str) -> float:
	"""
	Count leave days from Attendance (Half-Day = 0.5).
	"""
	records = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"leave_type": leave_type,
			"attendance_date": ("between", [from_date, to_date]),
			"status": ("in", ["On Leave", "Half Day"]),
			"docstatus": ["not in", [0,2]], # Not cancelled or draft
		},
		fields=["status"],
	)

	# full day = 1, half-day = 0.5
	return sum(0.5 if r.status == "Half Day" else 1.0 for r in records)


def get_leave_allocation_summary_attendance_based(from_date, to_date, employee):
    """Return a leave‑type wise summary for the employee within the requested window.

    For every active *Leave Type* the function shows how the balance moved
    during the period delimited by **from_date** and **to_date** (both
    inclusive):

    * **opening_balance** – balance on the day *before* ``from_date``.
    * **new_allocations** – fresh allocations whose *effective date* lies
      inside the window.
    * **consumed_leaves** – approved leave days whose *leave period* lies
      inside the window.
    * **closing_balance** – balance on ``to_date`` (opening + allocations − consumed).
    """

    # ─ 1 ─ validation ------------------------------------------------------
    if not all([from_date, to_date, employee]):
        frappe.throw(_("from_date, to_date and employee are required"))

    from_date = frappe.utils.getdate(from_date)
    to_date = frappe.utils.getdate(to_date)

    if from_date > to_date:
        frappe.throw(_("Start date cannot be after end date"))

    # ─ 2 ─ fetch active leave types ---------------------------------------
    leave_types = frappe.get_all(
        "Leave Type",
        fields=[
            "name",
            "is_lwp",
            "is_optional_leave",
            "is_compensatory",
        ],
    )

    # ─ 3 ─ anchors ---------------------------------------------------------
    day_before_window = frappe.utils.add_days(from_date, -1)

    # ─ 4 ─ crunch numbers --------------------------------------------------
    summary = []
    for lt in leave_types:
        lt_name = lt.name

        # Skip optional/LWP/compensatory when computing annual running totals
        is_countable = (
            lt.is_lwp == 0 and lt.is_optional_leave == 0 and lt.is_compensatory == 0
        )

        # ----- opening balance (as at day_before_window) -------------------
        opening_balance = 0.0
        if is_countable:
            opening_balance = (
                _allocated_on(employee, lt_name, day_before_window)
                - _leaves_taken(
                    employee,
                    lt_name,
                    from_date=frappe.utils.getdate(f"{from_date.year}-01-01"),
                    to_date=day_before_window,
                )
            )

        # ----- new allocations during the window --------------------------
        # We compute the delta between allocations effective up to to_date
        # minus allocations effective up to the day before the window.
        new_allocations = 0.0
        if is_countable:
            allocated_before = _allocated_on(employee, lt_name, day_before_window)
            allocated_until_end = _allocated_on(employee, lt_name, to_date)
            new_allocations = allocated_until_end - allocated_before

        # ----- leaves consumed inside the window ---------------------------
        consumed_leaves = _leaves_taken(
            employee, lt_name, from_date=from_date, to_date=to_date
        )

        # ----- closing balance --------------------------------------------
        closing_balance = opening_balance + new_allocations - consumed_leaves

        # Include row if there was any movement or non‑zero closing balance
        if any([
            opening_balance,
            new_allocations,
            consumed_leaves,
            closing_balance,
        ]):
            summary.append(
                {
                    "leave_type": lt_name,
                    "opening_balance": opening_balance,
                    "new_allocations": new_allocations,
                    "consumed_leaves": consumed_leaves,
                    "closing_balance": closing_balance,
                }
            )

    summary.sort(key=lambda r: r["leave_type"])
    return summary


# takes attendance records as input, returns hours in a float format
def get_hours_from_attendance(attendance_records, emp_working_hours, count_leaves):

	total_time = 0.0
	
	# Get the leave types first, so we know what is paid and what is not
	leave_types = frappe.db.get_all(
		"Leave Type",
		filters = {}, 
		fields = ["name", "is_lwp","is_optional_leave"]
	)

	for record in attendance_records:
		# If its a leave, we still have to count the hours
		
		if record.status == "Half Day" or record.status == "On Leave":

			# Only if the user wants us to count leaves
			if count_leaves == 1:
				for leave_type in leave_types: 
					if record.leave_type == leave_type.name:
						if leave_type.is_lwp == 0: # Skip leave without pay
							if record.status == "Half Day": 
								total_time = total_time + (emp_working_hours/2)
							else:
								total_time = total_time + emp_working_hours
		else: 
			total_time = total_time + record.working_hours

	return total_time

# Gets the holidays for the period
def get_holidays(holiday_list, from_date, to_date):
	# Fetch the holidays in the holiday list for the current year
	holidays = frappe.get_all('Holiday', fields=['holiday_date'], filters={
		'parent': holiday_list,
		'holiday_date': ['between', [from_date, to_date]]
	})

	# Count the holidays
	return len(holidays)

# Gets all timesheet data, grouped by activity type
def get_timesheet_data(employee, from_date, to_date):
	return frappe.db.sql(
		"""
		SELECT
			tsd.activity_type AS activity_type,
			SUM(tsd.hours) AS hours
		FROM `tabTimesheet` ts
		INNER JOIN `tabTimesheet Detail` tsd
			ON ts.name = tsd.parent
		WHERE ts.docstatus   = 1
		AND ts.employee	= %(employee)s
		AND ts.start_date >= %(start)s
		AND ts.end_date   <= %(end)s
		GROUP BY tsd.activity_type
		ORDER BY tsd.activity_type
		""",
		{"employee": employee, "start": from_date,  "end": to_date},
		as_dict=True,
	)


def enqueue_hours_calculation():
    # Push Swiss-hours run into a background queue.

    frappe.enqueue(
		method="swiss_accounting_software.swiss_qr_bill.doctype.swiss_hours_calculation.swiss_hours_calculation.run_hours_job",
		queue="long",
		timeout=60 * 30, # 30 mins wait
	)


def run_hours_job():
    """Actual worker job.  """
    frappe.logger().info("Swiss hours job started")
    create_hours_calculation()    # <- the code you pasted earlier
    frappe.logger().info("Swiss hours job finished")

# Creates the hours calculation from the daily scheduled script in hooks.py if no others already exist in the system
def create_hours_calculation():
	# Get the current date
	today = frappe.utils.getdate()
	current_day_int = int(today.strftime('%d'))


	# Fetch active settings for the current day
	calculation_settings = frappe.db.get_all(
		"Swiss Calculation Settings",
		filters={
			"enabled": 1,
			"generate_report_on": current_day_int
		},
		fields=["employment_type", "generate_report_on", "start_of_calculation", "end_of_calculation", "information"]
	)

	for setting in calculation_settings:
		# Calculate date range: 21st of previous month to 20th of current month (or whatever is configured)
		first_day_of_this_month = today.replace(day=1)
		previous_month = first_day_of_this_month - relativedelta(months=1)

		# Start date: configured day of previous month
		prev_month_start = previous_month.replace(day=setting.start_of_calculation)
		
		# End date: configured day of current month
		this_month_end = today.replace(day=setting.end_of_calculation)

		# Fetch relevant employees
		employees = frappe.db.get_all(
			"Employee",
			filters={
				"status": "Active",
				"employment_type": setting.employment_type
			},
			fields=["name", "date_of_joining", "relieving_date", "holiday_list"]
		)

		for employee in employees:
			# Check if calculation already exists for this employee and date range
			existing = frappe.db.exists(
				"Swiss Hours Calculation",
				{
					"employee": employee.name,
					"from_date": prev_month_start,
					"to_date": this_month_end
				}
			)

			if not existing:

				old_balance = 0.0

				# Check the db for the last hour balance
				latest_doc = frappe.get_all(
					"Swiss Hours Calculation", 
					filters={
						"employee": employee.name
					},
					fields=["name", "new_balance"], 
					order_by="to_date desc", 
					limit=1
				)

				if latest_doc: 
					old_balance = latest_doc[0].new_balance

				# Create new calculation document
				doc = frappe.new_doc("Swiss Hours Calculation")
				doc.status = "Open"
				doc.employee = employee.name
				doc.previous_hours = old_balance
				doc.from_date = prev_month_start
				doc.to_date = this_month_end
				doc.information = setting.information
				doc.insert()
				frappe.db.commit()