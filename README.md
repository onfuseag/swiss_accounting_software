## Swiss Accounting Software

ERPNexts functionality with Swiss QR Integration and payment automation

### Important information
This package has been updated to support Address Type “S” in accordance with the new Swiss banking standard taking effect in November 2025.

QR-bills are generated on the server with [chqr](https://github.com/balsigergil/chqr) (Swiss QR-bill specification v2.3). Submitting a Sales Invoice or clicking **Create QR Bill** attaches `{invoice}-QR.pdf` (invoice pages plus the QR payment slip).

Both a regular IBAN and a QR-IBAN are supported. Use **SCOR** or **NON** with a regular IBAN, and **QRR** with a QR-IBAN. Set the type in Swiss QR Bill Settings:

- **QRR** — QR-IBAN with a 27-digit QR reference
- **SCOR** — regular IBAN with an ISO 11649 creditor reference (RF…)
- **NON** — regular IBAN with no payment reference

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
