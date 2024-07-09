const path = require("path");

module.exports = {
  entry: "./src/index.js",
  output: {
    path: path.resolve(
      __dirname,
      "swiss_accounting_software",
      "public",
      "js"
    ),
    filename: "index.js",
  },
};
