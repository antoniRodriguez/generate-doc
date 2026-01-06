# layout-verifier

Product layout verification tool for checking consistency between Excel master data and PDF layout files.

---

## 1. Introduction

This utility verifies that product information in your Excel master data appears correctly in PDF layout files (product box designs).

Given an Excel file and a directory of PDF layouts, it:
- Reads product information from Excel (Item#, EAN, descriptions, etc.).
- Extracts text from PDF layout files using PyMuPDF.
- Matches each layout to its product via the Item# in the filename.
- Verifies that all expected text appears in the layout.
- Generates a verification report showing matches and discrepancies.

---

## 2. Use Case

Your company sells products where:
- Each product has static information (Item#, EAN, descriptions in multiple languages, etc.)
- This information exists in two sources:
  1. An Excel file (the ground truth)
  2. PDF layout files (2D box designs with text in various orientations)

The tool verifies that all information from the Excel appears in the corresponding PDF layout.

**Matching logic:**
- Layout files are matched to products by Item#
- The Item# is extracted from the PDF filename: the substring before the first space
- Example: `12345 Product Name v2.pdf` matches Item# `12345`

---

## 3. Requirements

- Python 3.10+
- No external services required (runs entirely locally)

---

## 4. Setup

1. **Create a Python virtual environment (optional but recommended)**

   In the project root:

       python -m venv venv

   Activate it:

   - WSL / bash:

         source venv/Scripts/activate

   - PowerShell:

         .\venv\Scripts\activate

2. **Install the project in editable mode**

   From the project root (where `pyproject.toml` lives):

       pip install -e .

---

## 5. Usage

### Batch Verification (Directory of PDFs)

    verify-layouts --excel products.xlsx --layouts-dir ./layouts/

Options:
- `--excel`, `-e`: Path to Excel file with product data (required)
- `--layouts-dir`, `-d`: Directory containing PDF layout files
- `--output`, `-o`: Output path for report (default: verification_report.md)
- `--format`, `-f`: Report format: `markdown`, `csv`, or `pdf` (default: markdown)
- `--columns`, `-C`: Specific columns to verify (optional, uses defaults)

### Single File Verification

    verify-layouts --excel products.xlsx --pdf "12345 Product Layout.pdf"

Options:
- `--pdf`, `-p`: Path to a single PDF file
- `--item`, `-i`: Override Item# (instead of extracting from filename)

### Examples

    # Verify all layouts in a directory
    verify-layouts -e data/products.xlsx -d data/layouts/ -o report.md

    # Generate CSV report for further processing
    verify-layouts -e products.xlsx -d layouts/ -f csv -o results.csv

    # Verify specific columns only
    verify-layouts -e products.xlsx -d layouts/ -C "Item#" "EAN" "Name ENG"

    # Verify a single file
    verify-layouts -e products.xlsx -p "12345 My Product.pdf"

---

## 6. Excel Format

The Excel file should have:
- One product per row
- Column headers in the first row
- An `Item#` column for matching to PDF filenames

Default columns verified (case-insensitive matching):
- `Item#` - Product identifier (used for matching, not verified)
- `EAN` - European Article Number / barcode
- `Serial` - Serial number
- `Name ENG` - English product name
- `Name ES`, `Name FR`, `Name DE`, `Name IT`, `Name PT` - Localized names
- `address under EAN/barcode` - Address text
- `origin (next to EAN/barcode)` - Country of origin
- `type of packaging` - Packaging type
- `Batch no:` - Batch number

You can specify custom columns using the `--columns` option.

---

## 7. PDF Layout Files

Requirements:
- PDF files with text content (not scanned images)
- Filename format: `<Item#> <anything>.pdf`
  - Example: `12345 Product Box Layout v3.pdf`
  - The Item# is extracted as everything before the first space

The tool uses PyMuPDF to extract text, which works well with:
- Vector text (text created in design software)
- Text at any orientation (horizontal, vertical, rotated)
- Multi-page PDFs

**Note:** If your PDFs are scanned images, you'll need OCR support (not included in this version).

---

## 8. Verification Logic

For each PDF layout:
1. Extract Item# from filename
2. Find matching product row in Excel
3. For each field in Excel:
   - Try exact match in PDF text
   - Try case-insensitive match
   - Try word-by-word match (for multi-word values split across lines)
   - Try numeric normalization (for EAN codes with/without separators)
4. Report which fields were found and which are missing

---

## 9. Output Reports

### Markdown Report
Human-readable report with:
- Summary statistics
- List of products with missing fields (showing what's missing)
- List of fully verified products

### CSV Report
Machine-readable format for further processing:
- One row per product
- Columns: Item#, Layout File, Total Fields, Matched, Missing, Success Rate, Status, Missing Fields

### PDF Report
Same content as Markdown, converted to PDF for sharing.

---

## 10. Project Structure

    layout-verifier/
    ├── pyproject.toml           # Package configuration
    ├── README.md                # This file
    ├── configs/
    │   └── project_config_template.json
    └── src/layout_verifier/
        ├── __init__.py          # Package exports
        ├── cli.py               # Command-line interface
        ├── core.py              # Main orchestration
        ├── excel_reader.py      # Excel file parsing
        ├── layout_reader.py     # PDF text extraction
        ├── verifier.py          # String matching logic
        ├── report_writer.py     # Report generation
        ├── logging_utils.py     # Console output formatting
        ├── spinner.py           # Progress indicator
        └── pdf_writer.py        # PDF report output

---

## 11. Programmatic Usage

You can also use the library programmatically:

```python
from layout_verifier import verify_layouts, verify_single_product

# Batch verification
summary = verify_layouts(
    excel_path="products.xlsx",
    layouts_dir="./layouts/",
    output_path="report.md",
    output_format="markdown"
)

print(f"Verified: {summary.products_verified}")
print(f"Complete: {summary.products_complete}")
print(f"Success rate: {summary.overall_success_rate:.1f}%")

# Single product verification
result = verify_single_product(
    excel_path="products.xlsx",
    pdf_path="12345 Product.pdf"
)

if result:
    print(f"Fields matched: {result['matched_fields']}/{result['total_fields']}")
```

---

## 12. Limitations

- PDF text extraction only (no OCR for scanned images)
- Assumes specific filename format (`Item# <rest>.pdf`)
- String matching may not catch all typography variations (fonts, special characters)
- Does not verify visual layout or positioning, only text presence
