# Test Documents Directory

Place documents here for local testing.

## Recommended Documents

- **invoice.pdf** - Product invoice or receipt
- **catalog.pdf** - Product catalog PDF
- **specs.pdf** - Product specifications sheet
- **pricelist.xlsx** - Price list spreadsheet
- **inventory.csv** - Inventory data

## Supported Formats

- PDF (.pdf) - Portable Document Format
- Excel (.xlsx, .xls) - Spreadsheets
- CSV (.csv) - Comma-separated values
- Word (.docx, .doc) - Word documents
- Text (.txt) - Plain text files

## Usage

```bash
# Test with PDF document
uv run python -m autifyme_agents.cli.pm_chat "Process this invoice" --media test_documents/invoice.pdf

# Test with spreadsheet
uv run python -m autifyme_agents.cli.simulate "Import this catalog" --media test_documents/pricelist.xlsx --auto-approve
```

## Creating Test Documents

You can create test documents by:
1. Exporting product data to Excel/CSV
2. Generating sample invoices
3. Creating mock product specification sheets
4. Downloading sample e-commerce documents
