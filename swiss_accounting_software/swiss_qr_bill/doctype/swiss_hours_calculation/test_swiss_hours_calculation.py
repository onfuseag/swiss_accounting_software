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

		hours_calculation.set_new_balance(doc, count_balance=1)
		self.assertEqual(doc.new_balance, -313.5)

		doc.correction = -2.5
		hours_calculation.set_new_balance(doc, count_balance=1)
		self.assertEqual(doc.new_balance, -318.5)

	def test_correction_only_with_zero_hours(self):
		doc = SimpleNamespace(
			previous_hours=0,
			worked_hours=0,
			required_hours=0,
			correction=-2.5,
			new_balance=None,
		)

		hours_calculation.set_new_balance(doc, count_balance=1)
		self.assertEqual(doc.new_balance, -2.5)

		hours_calculation.set_new_balance(doc, count_balance=0)
		self.assertEqual(doc.new_balance, -2.5)

	def test_count_balance_disabled_keeps_only_correction(self):
		doc = SimpleNamespace(
			previous_hours=4,
			worked_hours=160,
			required_hours=160,
			correction=2.5,
			new_balance=None,
		)

		hours_calculation.set_new_balance(doc, count_balance=0)
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
			new_balance=-316,
			additional=[],
			has_value_changed=Mock(return_value=True),
		)

		with (
			patch.object(hours_calculation.frappe.db, "get_value", return_value=1) as get_value,
			patch.object(hours_calculation, "calculate_hours_for_employee") as recalculate,
		):
			hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, -318.5)
		doc.has_value_changed.assert_called_once_with("correction")
		get_value.assert_called_once_with(
			"Swiss Calculation Settings",
			{"enabled": 1, "employment_type": "Full Time"},
			"count_balance",
		)
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
			new_balance=-318.5,
			additional=[],
			has_value_changed=Mock(side_effect=lambda field: field == "previous_hours"),
		)

		with (
			patch.object(hours_calculation.frappe.db, "get_value", return_value=1),
			patch.object(hours_calculation, "calculate_hours_for_employee") as recalculate,
		):
			hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, -315.5)
		doc.has_value_changed.assert_any_call("correction")
		doc.has_value_changed.assert_any_call("previous_hours")
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

		with patch.object(hours_calculation.frappe.db, "get_value", return_value=0):
			hours_calculation.SwissHoursCalculation.validate(doc)

		self.assertEqual(doc.new_balance, 3.5)

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

		with patch.object(hours_calculation.frappe.db, "get_value", return_value=None):
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
