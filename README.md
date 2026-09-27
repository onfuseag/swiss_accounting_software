## Swiss Accounting Software

ERPNexts functionality with Swiss QR Integration and payment automation

### Important information
This package has been updated to support Address Type “S” in accordance with the new Swiss banking standard taking effect in November 2025.

QR-bills are generated on the server with [chqr](https://github.com/balsigergil/chqr) (Swiss QR-bill specification v2.3). Submitting a Sales Invoice or clicking **Create QR Bill** attaches `{invoice}-QR.pdf` (invoice pages plus the QR payment slip).

Both a regular IBAN and a QR-IBAN are supported. Use **SCOR** or **NON** with a regular IBAN, and **QRR** with a QR-IBAN. Set the type in Swiss QR Bill Settings:

- **QRR** — QR-IBAN with a 27-digit QR reference
- **SCOR** — regular IBAN with an ISO 11649 creditor reference (RF…)
- **NON** — regular IBAN with no payment reference

### Informations de facture dans le QR

La communication contient le numéro et la date de la facture. Pour plusieurs
échéances, elle conserve également le rang du versement et sa date d'échéance.
Le compteur `1/1` n'apparaît plus pour un versement unique.

Le champ séparé d'informations de facturation utilise Swico S1 : `/10/` pour le
numéro et `/11/` pour la date de facture au format `YYMMDD`. L'IDE suisse de la
société, s'il est renseigné dans `Company.tax_id`, est ajouté sous `/30/`.
Les séparateurs présents dans un numéro de facture sont échappés. Les données S1
ne sont jamais tronquées ; la communication est raccourcie si les deux champs
dépassent ensemble 140 caractères. Un IDE non reconnu ou des données S1 trop
longues produisent une erreur explicite avant la génération du QR.
Pour un montant nul, la place du plus long avertissement de non-paiement de
`chqr` est réservée : son passage en français, allemand ou italien au rendu
ne peut pas faire dépasser les 140 caractères.
La communication imprimée est répartie sur plusieurs lignes dans le SVG,
sans changer les données du QR ni la référence ; le bloc du débiteur suit le
texte pour éviter les chevauchements.

La référence de paiement QRR/SCOR et les montants sont indépendants de ces
informations. Les champs S1 servent au destinataire de la facture et ne sont pas
transmis au créancier avec le paiement.

Contrôle ciblé (Python 3.10 ou supérieur, dépendance `chqr` installée) :
`python -m unittest discover -s tests -v`.
Le [protocole d'essai ERPNext et de contrôle du rendu](docs/verification-qr-invoice.md)
précise les vérifications faites et celles qui restent à réaliser.

### Wiki
Guides are available on [docs.onfuse.ch/swiss-accounting-software](https://docs.onfuse.ch/swiss-accounting-software/)

### Structure

App Contains 4 Modules

1. Abacus Exports
2. Swiss QR Bill
3. CAMT Import for switzerland
4. Pain.001 integration for switzerland

#### Swiss QR Bill

It Contains 1 Doctype Called **Swiss QR Bill Settings**

In order to Setup QR Bill to Working Following Things are Required

1. Create A Company With Proper Address
2. Create A Customer with Proper Address and Language
3. Create A Bank Account For Company with IBAN or QR-IBAN
4. Add Entry in Swiss QR Bill Settings for Company (QR Code Type QRR, SCOR, or NON)

#### License

GNU GPL V3
