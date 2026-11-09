# Swiss Accounting Software

ERPNext functionality for Swiss labour, banking, and QR bills.

## Wiki

Guides are available at
[docs.onfuse.ch/swiss-accounting-software](https://docs.onfuse.ch/swiss-accounting-software/).

## Structure

### Swiss Labour

- Swiss Hours Calculation
- Swiss Calculation Settings
- Frappe HR: Attendance, Employee Checkin, Shift Type, Shift Assignment,
  Leave Application, Leave Allocation, and Timesheet

### Swiss Finance

- Bank Statement Import
- Bank Transaction
- Swiss QR Bill Settings
- Steuerziffer CH

#### Payment Information

The invoice number and date are included as structured Swico S1 billing
information in the QR code and printed under the translated **Additional
information** heading. Multiple installments retain their counters and due
dates; a single installment omits the `1/1` counter.

**Include Tax ID in Payment Information** adds the company's Swiss tax ID from
`Company.tax_id` when available. The setting is off by default. Optional payment
descriptions are shortened to fit the shared 140-character limit while
preserving structured data and installment details.

#### QR Bills

QR bills are generated on the server with
[chqr](https://github.com/balsigergil/chqr) using Swiss QR-bill specification
v2.3. Submitting a Sales Invoice or clicking **Create QR Bill** attaches
`{invoice}-QR.pdf` with the invoice pages and QR payment slip.

Both regular IBANs and QR-IBANs are supported. Select the QR code type in Swiss
QR Bill Settings:

- **QRR:** QR-IBAN with a 27-digit QR reference
- **SCOR:** regular IBAN with an ISO 11649 creditor reference
- **NON:** regular IBAN without a payment reference

Set up a company, customer, and company bank account with valid addresses, then
configure Swiss QR Bill Settings for the company. Address Type “S” is supported
under the Swiss banking standard effective November 2025.

## License

GNU GPL v3
