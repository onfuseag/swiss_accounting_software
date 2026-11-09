## Swiss Accounting Software

ERPNexts functionality with Swiss QR Integration and payment automation

### Desk navigation

Swiss Accounting Software has **Swiss Finance** and **Swiss Labour** sidebars in
the Swiss QR Bill module, following the same multi-sidebar structure as Elevator.
Swiss Finance links to Bank Statement Import, Bank Transaction, Swiss QR Bill
Settings, and Steuerziffer CH. Swiss Labour links to Swiss Hours Calculation and
Swiss Calculation Settings. Its **Frappe HR** section links to Attendance,
Employee Checkin, Shift Type, Shift Assignment, Leave Application, Leave
Allocation, and Timesheet.

After updating the app, run `bench --site <site> migrate` to import the standard
Sidebar and Dock records, then reload Desk. The existing app icon is reused.

### Important information
This package has been updated to support Address Type “S” in accordance with the new Swiss banking standard taking effect in November 2025.

QR-bills are generated on the server with [chqr](https://github.com/balsigergil/chqr) (Swiss QR-bill specification v2.3). Submitting a Sales Invoice or clicking **Create QR Bill** attaches `{invoice}-QR.pdf` (invoice pages plus the QR payment slip).

Both a regular IBAN and a QR-IBAN are supported. Use **SCOR** or **NON** with a regular IBAN, and **QRR** with a QR-IBAN. Set the type in Swiss QR Bill Settings:

- **QRR** — QR-IBAN with a 27-digit QR reference
- **SCOR** — regular IBAN with an ISO 11649 creditor reference (RF…)
- **NON** — regular IBAN with no payment reference

### Payment information

The invoice number and date are included as structured Swico S1 billing information
in the QR code and printed under the translated **Additional information** heading
on the payment section. There is no default English invoice description. Multiple
installments keep their `1/2`, `2/2`, etc. counters and due dates; a single
installment omits `1/1`.

**Include Tax ID in Payment Information** in Swiss QR Bill Settings adds the
company's Swiss tax ID (UID) from `Company.tax_id`, when available. It is off by
default. Run `bench --site <site> migrate` and reload Desk after updating to add
the new setting.

Optional payment descriptions are shortened to fit the shared 140-character limit;
structured data and installment counters/due dates are preserved. QR headings
continue to use the invoice language.

Run the QR tests with `python3 -m unittest discover -s tests -v` after installing
the project's dependencies.

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
