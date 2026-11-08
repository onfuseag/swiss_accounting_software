"""Show both parts of the QR-bill payment information in the printed SVG."""

import textwrap
import xml.etree.ElementTree as ET

from chqr.constants import TRANSLATIONS

SVG = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", SVG[1:-1])
# At 10 pt, 24 characters fit the right-hand payment column, even when wide.
MESSAGE_LINE_LENGTH = 24
MAX_INFORMATION_LINES = 7
INFORMATION_LABELS = {labels["additional_information"] for labels in TRANSLATIONS.values()}
PAYABLE_BY_LABELS = {labels["payable_by"] for labels in TRANSLATIONS.values()}


def _message_lines(message: str, billing_line_count: int = 0) -> list[str]:
	lines = textwrap.wrap(message, width=MESSAGE_LINE_LENGTH,
		break_long_words=True, break_on_hyphens=False)
	if len(lines) + billing_line_count > MAX_INFORMATION_LINES:
		# Word wrapping can waste nearly half a line for wide words. Split at
		# fixed widths when it would push the debtor below the payment part.
		lines = [message[i:i + MESSAGE_LINE_LENGTH]
			for i in range(0, len(message), MESSAGE_LINE_LENGTH)]
	return lines


def _billing_lines(information: str) -> list[str]:
	# S1 is machine-readable text; preserve every character, including spaces in
	# an invoice number, when splitting it across printed lines.
	return [information[i:i + MESSAGE_LINE_LENGTH]
		for i in range(0, len(information), MESSAGE_LINE_LENGTH)]


def wrap_additional_information(
	svg_content: str, message: str | None, billing_information: str | None = None,
) -> str:
	"""Wrap the message and print the structured S1 field below it.

	chqr puts the structured field in the QR payload but omits it from its SVG.
	The printed field shares chqr's translated Additional information heading.
	"""
	if not billing_information and (not message or len(message) <= MESSAGE_LINE_LENGTH):
		return svg_content

	root = ET.fromstring(svg_content)
	parent = root.find(f".//{SVG}text[@x='51mm'][@y='-4.76mm']")
	if parent is None:
		raise ValueError("Could not find the payment information column in the chqr SVG.")

	children = list(parent)
	billing_lines = _billing_lines(billing_information or "")
	if message:
		for index, span in enumerate(children):
			if (span.tag == SVG + "tspan" and span.get("x") == "51mm"
				and span.text == message and index > 0
				and children[index - 1].get("font-weight") == "bold"
				and children[index - 1].text in INFORMATION_LABELS):
				break
		else:
			raise ValueError("Could not find the payment description in the chqr SVG.")

		lines = _message_lines(message, len(billing_lines))
		span.text = lines[0]
		span.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
		for offset, line in enumerate(lines[1:], 1):
			continuation = ET.Element(SVG + "tspan", dict(span.attrib))
			continuation.text = line
			parent.insert(index + offset, continuation)
		index += len(lines)
	else:
		# chqr only emits the heading when an unstructured message exists.
		# Place the same translated heading before the debtor when S1 stands alone.
		index = next((i for i, span in enumerate(children)
			if span.get("font-weight") == "bold"
			and span.text in PAYABLE_BY_LABELS),
			len(children))
		account_heading = children[0].text if children else ""
		language = next((lang for lang, labels in TRANSLATIONS.items()
			if account_heading == labels["account_payable_to"]), "en")
		heading = ET.Element(SVG + "tspan", {
			"x": "51mm", "dy": "22pt", "font-size": "8pt", "font-weight": "bold",
		})
		heading.text = TRANSLATIONS[language]["additional_information"]
		parent.insert(index, heading)
		index += 1

	for line in billing_lines:
		printed = ET.Element(SVG + "tspan", {
			"x": "51mm", "dy": "11pt", "font-size": "10pt",
			"{http://www.w3.org/XML/1998/namespace}space": "preserve",
		})
		printed.text = line
		parent.insert(index, printed)
		index += 1

	# Relative line positions move the debtor down without changing QR data.
	return ET.tostring(root, encoding="unicode")
