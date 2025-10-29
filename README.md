## Swiss Accounting Software

ERPNexts functionality with Swiss QR Integration and payment automation

### Important information
This package has been updated to support Address Type “S” in accordance with the new Swiss banking standard taking effect in November 2025.
It is recommended to clear the browser cache in order to geneerate the updated invoice.

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
3. Create A Bank Account For Company with IBAN
4. Add Entry in Swiss QR Bill Settings for Company

### To build updated js code
```
npx webpack --config webpack.config.js
Bench build
Bench restart
```

#### License

GNU GPL V3
