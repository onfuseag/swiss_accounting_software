# Copyright (c) 2025, ONFUSE AG and Contributors
# See license.txt

from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frappe.tests.utils import FrappeTestCase

from . import swiss_hours_calculation as hours_calculation


class TestSwissHoursCalculation(FrappeTestCase):
	def test_signed_correction_changes_new_balance(self):
		doc = SimpleNamespace(
			previous_hours=4,
			worked_hours=160,
			required_hours=160,
			correction=2.5,
			new_balance=None,
		)

		hours_calculation.set_new_balance(doc)
		self.assertEqual(doc.new_balance, 6.5)

		doc.correction = -2.5
		hours_calculation.set_new_balance(doc)
		self.assertEqual(doc.new_balance, 1.5)

	def test_correction_only_with_zero_hours(self):
		doc = SimpleNamespace(
			previous_hours=0,
			worked_hours=0,
			required_hours=0,
			correction=-2.5,
			new_balance=None,
		)

		hours_calculation.set_new_balance(doc)
		self.assertEqual(doc.new_balance, -2.5)

		doc.required_hours = None
		doc.worked_hours = None
		hours_calculation.set_new_balance(doc)
		self.assertEqual(doc.new_balance, -2.5)

	def test_empty_required_and_worked_hours_count_as_zero(self):
		doc = SimpleNamespace(
			previous_hours=4,
			worked_hours=None,
			required_hours=None,
			correction=2.5,
			new_balance=None,
		)

		hours_calculation.set_new_balance(doc)
		self.assertEqual(doc.new_balance, 6.5)

		doc.previous_hours = None
		hours_calculation.set_new_balance(doc)
		self.assertEqual(doc.previous_hours, 0)
		self.assertEqual(doc.new_balance, 2.5)

	def test_edited_correction_on_done_draft_updates_balance_only(self):
		doc = SimpleNamespace(
			status="Done",
			docstatus=0,
			employment_type="Full Time",
			previous_hours=4,
			worked_hours=160,
			required_hours=160,
			correction=-2.5,
			new_balance=4,
			additional=[],
			has_value_changed=Mock(return_value=True),
		)

		with patch.object(hours_calculation, "calculate_hours_for_employee") as recalculate:
			hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, 1.5)
		recalculate.assert_not_called()

	def test_fetched_previous_hours_on_done_draft_updates_balance(self):
		doc = SimpleNamespace(
			status="Done",
			docstatus=0,
			employment_type="Full Time",
			previous_hours=7,
			worked_hours=160,
			required_hours=160,
			correction=-2.5,
			new_balance=1.5,
			additional=[],
			has_value_changed=Mock(side_effect=lambda field: field == "previous_hours"),
		)

		with patch.object(hours_calculation, "calculate_hours_for_employee") as recalculate:
			hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, 4.5)
		recalculate.assert_not_called()

	def test_correction_only_on_done_draft_updates_balance(self):
		doc = SimpleNamespace(
			status="Done",
			docstatus=0,
			employment_type="Full Time",
			previous_hours=0,
			worked_hours=0,
			required_hours=0,
			correction=3.5,
			new_balance=0,
			additional=[],
			has_value_changed=Mock(side_effect=lambda field: field == "correction"),
		)

		hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, 3.5)

	def test_done_draft_with_empty_hours_and_missing_balance_recalculates(self):
		doc = SimpleNamespace(
			status="Done",
			docstatus=0,
			employment_type="Full Time",
			previous_hours=4,
			worked_hours=None,
			required_hours=None,
			correction=2.5,
			new_balance=None,
			additional=[],
			has_value_changed=Mock(return_value=False),
		)

		hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, 6.5)

	def test_new_draft_with_empty_hours_and_correction_recalculates(self):
		doc = SimpleNamespace(
			status=None,
			docstatus=0,
			employment_type="Full Time",
			previous_hours=None,
			worked_hours=None,
			required_hours=None,
			correction=2.5,
			new_balance=None,
			additional=[],
			has_value_changed=Mock(return_value=True),
		)

		hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, 2.5)

	def test_correction_only_on_new_draft_without_settings(self):
		doc = SimpleNamespace(
			status=None,
			docstatus=0,
			employment_type="Full Time",
			previous_hours=0,
			worked_hours=0,
			required_hours=0,
			correction=3.5,
			new_balance=None,
			additional=[],
			has_value_changed=Mock(return_value=True),
		)

		hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, 3.5)

	def test_open_draft_without_settings_keeps_correction(self):
		doc = SimpleNamespace(
			status="Open",
			date_of_joining=date(2026, 1, 1),
			from_date=date(2026, 2, 1),
			to_date=date(2026, 2, 28),
			relieving_date=None,
			employment_type="Full Time",
			previous_hours=0,
			worked_hours=0,
			required_hours=0,
			correction=3.5,
			new_balance=None,
			leaves=[],
			timesheets=[],
		)

		with (
			patch.object(hours_calculation.frappe, "get_single", return_value=SimpleNamespace()),
			patch.object(hours_calculation.frappe.db, "get_all", return_value=[]),
		):
			hours_calculation.calculate_hours_for_employee(doc)

		self.assertEqual(doc.new_balance, 3.5)

	def test_open_draft_with_empty_configured_and_attendance_hours(self):
		doc = SimpleNamespace(
			status="Open",
			date_of_joining=date(2026, 1, 1),
			from_date=date(2026, 2, 1),
			to_date=date(2026, 2, 1),
			relieving_date=None,
			employee="EMP-001",
			employment_type="Full Time",
			previous_hours=5,
			worked_hours=None,
			required_hours=None,
			correction=2,
			new_balance=None,
			leaves=[],
			timesheets=[],
			additional=[],
			append=Mock(),
		)
		setting = SimpleNamespace(
			working_hours=None,
			count_leaves=0,
			count_balance=1,
			timesheet_activities=[],
			monthly_allowance=0,
		)

		with (
			patch.object(hours_calculation.frappe, "get_single", return_value=SimpleNamespace(standard_working_hours=None)),
			patch.object(hours_calculation.frappe.db, "get_all", return_value=[{"name": "SET-001"}]),
			patch.object(hours_calculation.frappe, "get_doc", return_value=setting),
			patch.object(hours_calculation.frappe.db, "get_value", side_effect=[(None, "Company"), None]),
			patch.object(hours_calculation.frappe.utils, "date_diff", return_value=0),
			patch.object(hours_calculation.frappe, "get_all", return_value=[]),
			patch.object(hours_calculation, "get_hours_from_attendance", return_value=0),
			patch.object(hours_calculation, "get_timesheet_data", return_value=[]),
			patch.object(hours_calculation, "get_timesheet_allowance_daily", return_value=0),
			patch.object(hours_calculation, "get_leave_allocation_summary_attendance_based", return_value=[]),
		):
			hours_calculation.calculate_hours_for_employee(doc)

		self.assertEqual(doc.required_hours, 0)
		self.assertEqual(doc.worked_hours, 0)
		self.assertEqual(doc.new_balance, 7)
		self.assertEqual(doc.status, "Done")

	def test_attendance_with_empty_working_hours_counts_zero(self):
		records = [
			SimpleNamespace(status="Present", working_hours=None, leave_type=None),
			SimpleNamespace(status="Half Day", working_hours=None, leave_type=None),
		]

		with patch.object(hours_calculation.frappe.db, "get_all", return_value=[]):
			hours = hours_calculation.get_hours_from_attendance(records, emp_working_hours=0, count_leaves=0)

		self.assertEqual(hours, 0)
