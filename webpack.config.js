const path = require("path");
const webpack = require('webpack');

module.exports = {
  mode: "production",
  entry: "./src/index.js",
  resolve: {
    fallback: { fs: false }
  },
  plugins: [
    // needed by pdfkit/browser stack
    new webpack.ProvidePlugin({
      Buffer: ['buffer', 'Buffer'],
      process: 'process/browser'
    })
  ],
  output: {
    
    path: path.resolve(
      __dirname,
      "swiss_accounting_software",
      "public",
      "js"
    ),
    filename: "index.bundle.js",
  },
};
