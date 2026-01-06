# src/docgen/__init__.py
#
# Package init for layout-verifier.

from .core import verify_layouts, verify_single_product
from .excel_reader import load_product_data, get_product_by_item_number
from .layout_reader import extract_text_from_layout, extract_text_from_ai, scan_layout_directory, extract_barcodes_from_layout
from .verifier import verify_product_fields, VerificationSummary

__all__ = [
    "verify_layouts",
    "verify_single_product",
    "load_product_data",
    "get_product_by_item_number",
    "extract_text_from_layout",
    "extract_text_from_ai",
    "extract_barcodes_from_layout",
    "scan_layout_directory",
    "verify_product_fields",
    "VerificationSummary",
]
