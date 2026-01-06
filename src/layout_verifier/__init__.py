# src/layout_verifier/__init__.py
#
# Package init for layout-verifier.

from .core import verify_layouts, verify_single_product, verify_and_color_excel
from .excel_reader import load_product_data, get_product_by_item_number
from .layout_reader import extract_text_from_layout, extract_text_from_ai, scan_layout_directory, extract_barcodes_from_layout
from .verifier import verify_product_fields, VerificationSummary
from .excel_colorizer import color_excel_cells, ColoringResult

__all__ = [
    # Main entry points
    "verify_and_color_excel",
    "verify_layouts",
    "verify_single_product",
    # Excel utilities
    "load_product_data",
    "get_product_by_item_number",
    "color_excel_cells",
    "ColoringResult",
    # Layout utilities
    "extract_text_from_layout",
    "extract_text_from_ai",
    "extract_barcodes_from_layout",
    "scan_layout_directory",
    # Verification
    "verify_product_fields",
    "VerificationSummary",
]
