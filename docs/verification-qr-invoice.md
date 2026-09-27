# Essai de la proposition d'informations de facture

Cette procédure concerne la proposition du fil #18. Elle distingue les tests
du contenu QR de l'essai complet dans ERPNext v16. Utiliser une instance de test
et des factures inventées ; ne déclencher aucun paiement.

## Tests automatisés du contenu

Depuis la racine du projet, avec Python 3.10 ou supérieur et `chqr` installé :

```sh
python -m unittest discover -s tests -v
```

Résultat mesuré avec Python 3.13 et chqr 1.2.5 : 17 tests réussis.
Les accès Frappe y sont simulés. Les contenus QR, les références, les montants
et les SVG utilisent la vraie bibliothèque chqr. Les fichiers réels sont
chargés sans exécuter l'initialisation générale de l'application, qui exige
un site Frappe. La commande fonctionne depuis le dépôt complet.

## Contrôle indépendant effectué

Les SVG complets générés par chqr puis mis en forme par la proposition,
avec la croix suisse, ont été rendus en PNG
à 300 dpi par librsvg 2.62.0, puis décodés par Apple Vision. Les 26 lectures
restituent exactement le contenu attendu ; une image blanche témoin ne donne
aucun QR. Cas : QRR/SCOR/NON dans les quatre langues, montant nul dans les
quatre langues, limite de longueur avec montant nul dans les quatre langues,
numéro avec accent et séparateurs, communication longue, deux versements et deux cas de lettres particulièrement larges.

Ce contrôle ne reproduit ni le PDF produit par wkhtmltopdf, ni le parcours
ERPNext, ni les règles d'acceptation d'une application bancaire.

## Essai dans ERPNext v16, à réaliser

Relever les versions de Frappe, ERPNext, de cette application et de chqr.
Préparer les réglages de QR-facture, la banque et les adresses structurées
sur une société de test. Noter la référence QRR et les montants avant le patch.

| Cas | Contrôle attendu |
|---|---|
| Facture normale, numéro `DEMO-2026-00001`, date 15.01.2026 | Communication avec numéro/date ; S1 `/10/DEMO-2026-00001/11/260115` ; référence et montant identiques à ceux d'avant le patch. |
| Échéance unique le 15.02.2026 | Pas de `1/1` ; `/11/` conserve la date de facture 15.01.2026. |
| Deux échéances | Deux sections de paiement, montants attendus et repères `1/2`, `2/2` conservés dans la place disponible. |
| Société avec IDE suisse dans `Company.tax_id` | Tag `/30/` avec les neuf chiffres de l'IDE. |
| Numéro contenant `/` ou `\` | Numéro lisible ; séparateurs échappés dans S1. |
| Montant nul | Avertissement complet dans chaque langue ; total des deux champs inférieur ou égal à 140, y compris après le rendu. |
| Numéro très long ou IDE non reconnu | Erreur explicite ; confirmer avec les mainteneurs que ce comportement convient. |
| Facture imprimée ou PDF | Texte lisible sans débordement ni chevauchement ; QR relisible depuis le PDF final. |

Contrôler les deux déclencheurs de génération : soumission de la facture et
action « Create QR Bill ». Vérifier ensuite la pièce jointe et le rapprochement
fondé sur la référence déjà utilisée, sur les données de test.

## Affichage des communications longues

Le rendu chqr 1.2.5 place initialement la communication sur une seule ligne.
La proposition la répartit dans le SVG en lignes de 24 caractères au plus,
avec les mêmes taille et hauteur de ligne. Les lignes du débiteur descendent
avec le texte. Le contenu encodé dans le QR est inchangé.

Les tests contrôlent la conservation du texte, les longues suites de lettres
larges, les caractères XML, la place verticale du débiteur et l'utilisation
du rendu adapté à l'entrée du convertisseur PDF pour chaque échéance. Le
rendu réel avec wkhtmltopdf reste à vérifier dans l'installation ERPNext.

## Avis attendu des mainteneurs

- Confirmer le champ de société utilisé pour l'IDE et le traitement d'un IDE
  non reconnu.
- Confirmer le rendu des communications longues et les factures échelonnées.
- Accepter ou adapter le patch avant son intégration officielle.
