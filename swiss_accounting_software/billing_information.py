"""Build invoice descriptions and structured Swico S1 billing information."""

from datetime import date, datetime
import re

MAX_INFORMATION_LENGTH = 140


def invoice_date(value) -> date:
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value))


def invoice_message(number: str, posting_date) -> str:
	return f"Invoice {number} dated {invoice_date(posting_date):%d.%m.%Y}"


def billing_information(number: str, posting_date, tax_id: str | None = None) -> str:
	if not number or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in number):
		raise ValueError("Invoice number must be nonempty and contain no control characters.")
	escaped = number.replace("\\", "\\\\").replace("/", "\\/")
	information = f"//S1/10/{escaped}/11/{invoice_date(posting_date):%y%m%d}"
	if tax_id and tax_id.strip():
		match = re.fullmatch(
			r"(?:CHE[-\s]?)?([0-9]{3})[.\s]?([0-9]{3})[.\s]?([0-9]{3})"
			r"(?:\s*(?:MWST|TVA|IVA|VAT)(?:\s*/\s*(?:MWST|TVA|IVA|VAT))*)?",
			tax_id.strip(),
			re.IGNORECASE,
		)
		if not match:
			raise ValueError(
				"Company Tax ID must be a Swiss UID, for example CHE-123.456.789. "
				"Correct it or disable Include Tax ID in Payment Information."
			)
		information += "/30/" + "".join(match.groups())
	if len(information) > MAX_INFORMATION_LENGTH:
		raise ValueError("Structured billing information exceeds 140 characters. Use a shorter invoice number.")
	return information


def fit_message(message: str | None, information: str, installment: str | None = None) -> str | None:
	"""Shorten the description while preserving S1 data and installment details."""
	available = MAX_INFORMATION_LENGTH - len(information)
	if available < 0:
		raise ValueError("Structured billing information exceeds 140 characters.")
	text = " ".join((message or "").split())
	prefix = " ".join((installment or "").split())
	if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in text + prefix):
		raise ValueError("Payment information contains a control character.")
	if len(prefix) > available:
		raise ValueError("Invoice information leaves no room for installment details. Use a shorter invoice number.")
	if prefix:
		available -= len(prefix) + 3  # Reserve the separator before the invoice description.
	if len(text) > available:
		text = text[: available - 3].rstrip() + "..." if available > 3 else ""
	return " - ".join(part for part in (prefix, text) if part) or None
