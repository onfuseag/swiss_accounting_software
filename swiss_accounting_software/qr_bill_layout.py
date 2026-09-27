"""Retour à la ligne de la communication dans le SVG produit par chqr."""

import textwrap
import xml.etree.ElementTree as ET

from chqr.constants import TRANSLATIONS

SVG = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", SVG[1:-1])
# La colonne fait 87 mm. À 10 pt, 24 caractères de largeur 1 em tiennent
# dans 85 mm. Cette borne prudente couvre aussi les longues suites de W.
MESSAGE_LINE_LENGTH = 24
INFORMATION_LABELS = {labels["additional_information"] for labels in TRANSLATIONS.values()}


def wrap_additional_information(svg_content: str, message: str) -> str:
	if not message or len(message) <= MESSAGE_LINE_LENGTH:
		return svg_content
	root = ET.fromstring(svg_content)
	for parent in root.iter(SVG + "text"):
		children = list(parent)
		for index, span in enumerate(children):
			if (span.tag != SVG + "tspan" or span.get("x") != "51mm"
				or span.text != message or index == 0
				or children[index - 1].get("font-weight") != "bold"
				or children[index - 1].text not in INFORMATION_LABELS):
				continue
			lines = textwrap.wrap(message, width=MESSAGE_LINE_LENGTH,
				break_long_words=True, break_on_hyphens=False)
			span.text = lines[0]
			for offset, line in enumerate(lines[1:], 1):
				continuation = ET.Element(SVG + "tspan", dict(span.attrib))
				continuation.text = line
				parent.insert(index + offset, continuation)
			# Les lignes suivantes utilisent déjà dy : le débiteur descend avec
			# la communication. Le QR et son contenu ne sont pas modifiés.
			return ET.tostring(root, encoding="unicode")
	raise ValueError("La communication à mettre en forme est introuvable dans le SVG chqr.")
