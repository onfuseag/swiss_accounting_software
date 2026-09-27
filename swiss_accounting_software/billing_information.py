"""Informations de facture Swico S1 ; aucune modification de la référence de paiement."""

from datetime import date, datetime
import re

MAX_INFORMATION_LENGTH = 140


def invoice_date(value) -> date:
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value))


def invoice_message(number: str, posting_date, language: str = "de") -> str:
	day = invoice_date(posting_date).strftime("%d.%m.%Y")
	labels = {
		"de": ("Rechnung", "vom"),
		"en": ("Invoice", "dated"),
		"fr": ("Facture", "du"),
		"it": ("Fattura", "del"),
	}
	label, connector = labels.get(language, labels["de"])
	return f"{label} {number} {connector} {day}"


def billing_information(number: str, posting_date, tax_id: str | None = None) -> str:
	# Swico S1 1.2 : /10/ numéro, /11/ date de facture, /30/ IDE si renseigné.
	if not number or any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in number):
		raise ValueError("Le numéro de facture doit être non vide et tenir sur une ligne.")
	escaped = number.replace("\\", "\\\\").replace("/", "\\/")
	information = f"//S1/10/{escaped}/11/{invoice_date(posting_date):%y%m%d}"
	if tax_id and tax_id.strip():
		match = re.fullmatch(
			r"(?:CHE[-\s]?)?(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})(?:\s*(?:MWST|TVA|IVA|VAT))?",
			tax_id.strip(),
			re.IGNORECASE,
		)
		if not match:
			raise ValueError("Le numéro fiscal de la société doit être un IDE suisse pour les informations S1.")
		information += "/30/" + "".join(match.groups())
	if len(information) > MAX_INFORMATION_LENGTH:
		raise ValueError("Les informations S1 dépassent 140 caractères ; le numéro de facture ne peut pas être tronqué.")
	return information


def fit_message(message: str | None, information: str) -> str | None:
	# SIX 2.3 §4.3.3 : 140 caractères pour les DEUX champs réunis.
	available = MAX_INFORMATION_LENGTH - len(information)
	if available < 0:
		raise ValueError("Les informations S1 dépassent 140 caractères.")
	text = " ".join((message or "").split())
	if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in text):
		raise ValueError("La communication contient un caractère de contrôle.")
	if len(text) <= available:
		return text or None
	if available <= 3:
		return None
	return text[: available - 3].rstrip() + "..."
