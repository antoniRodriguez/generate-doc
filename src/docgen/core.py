# src/docgen/core.py
#
# High-level orchestration for product layout verification:
# - Load product data from Excel
# - Scan layout directory for PDF files
# - For each layout: extract text, match to product, verify fields
# - Generate verification report

from pathlib import Path
from typing import Optional

from .excel_reader import load_product_data, get_product_by_item_number, get_verification_fields
from .layout_reader import scan_layout_directory, extract_text_from_layout
from .verifier import verify_product_fields, VerificationSummary
from .report_writer import generate_report, save_report
from .spinner import Spinner
from .logging_utils import log_info, log_warning, log_error


def verify_layouts(
    excel_path: str,
    layouts_dir: str,
    output_path: Optional[str] = None,
    output_format: str = "markdown",
    columns: Optional[list[str]] = None,
    extension: str = ".ai",
) -> VerificationSummary:
    """
    Verify product information consistency between Excel and layout files.

    Main orchestration function that:
    1. Loads product master data from Excel
    2. Scans the layouts directory for layout files (.ai or .pdf)
    3. For each layout, extracts text and verifies against Excel data
    4. Generates a verification report

    Args:
        excel_path: Path to the Excel file with product master data.
        layouts_dir: Directory containing layout files.
        output_path: Path for the output report (optional).
        output_format: Report format - "markdown", "pdf", or "csv".
        columns: List of Excel columns to verify (optional, uses defaults if not provided).
        extension: File extension to scan for (default: ".ai").

    Returns:
        VerificationSummary with all verification results.
    """

    # 1) Load product data from Excel
    log_info(f"Loading product data from '{excel_path}'...")
    try:
        products_df = load_product_data(excel_path, columns=columns)
    except (FileNotFoundError, ValueError) as e:
        log_error(f"Failed to load Excel: {e}")
        raise

    log_info(f"Loaded {len(products_df)} products from Excel.")

    # 2) Initialize summary
    summary = VerificationSummary(total_products=len(products_df))

    # 3) Scan layouts directory and verify each
    log_info(f"Scanning layouts directory: {layouts_dir}")

    spinner = Spinner("Verifying layouts...")
    spinner.start()

    try:
        layouts_processed = 0
        for layout_path, item_number in scan_layout_directory(layouts_dir, extension=extension):
            layouts_processed += 1

            # Get product data from Excel
            product_data = get_product_by_item_number(products_df, item_number)

            if product_data is None:
                log_warning(f"No Excel entry for Item# '{item_number}' ({layout_path.name})")
                summary.add_unmatched_layout(layout_path.name)
                continue

            # Extract fields to verify
            expected_fields = get_verification_fields(product_data)

            if not expected_fields:
                log_warning(f"No fields to verify for Item# '{item_number}'")
                continue

            # Extract text from layout file
            try:
                layout_text = extract_text_from_layout(layout_path)
            except (FileNotFoundError, ValueError) as e:
                log_error(f"Failed to read layout {layout_path.name}: {e}")
                continue

            # Verify fields
            result = verify_product_fields(
                item_number=item_number,
                layout_file=layout_path.name,
                expected_fields=expected_fields,
                layout_text=layout_text,
            )

            summary.add_result(result)

    finally:
        spinner.stop()

    log_info(f"Processed {layouts_processed} layout files.")
    log_info(
        f"Results: {summary.products_complete} complete, "
        f"{summary.products_partial} partial, "
        f"{summary.layouts_without_match} unmatched"
    )

    # 4) Generate and save report
    if output_path:
        log_info(f"Generating {output_format} report...")
        report_content = generate_report(summary, output_format)
        save_report(report_content, output_path, output_format)
        log_info(f"Report saved to '{output_path}'.")
    else:
        # Default output path
        output_path = str(Path(layouts_dir).parent / "verification_report.md")
        log_info(f"Generating report at default location...")
        report_content = generate_report(summary, "markdown")
        save_report(report_content, output_path, "markdown")
        log_info(f"Report saved to '{output_path}'.")

    return summary


def verify_single_product(
    excel_path: str,
    layout_path: str,
    item_number: Optional[str] = None,
    columns: Optional[list[str]] = None,
) -> Optional[dict]:
    """
    Verify a single product layout against Excel data.

    Useful for testing or verifying individual files.

    Args:
        excel_path: Path to the Excel file with product master data.
        layout_path: Path to a single layout file (.ai or .pdf).
        item_number: The Item# to look up (if None, extracted from filename).
        columns: List of Excel columns to verify.

    Returns:
        Dictionary with verification result, or None if verification failed.
    """
    from .layout_reader import extract_item_number_from_filename

    # Determine item number
    if item_number is None:
        item_number = extract_item_number_from_filename(layout_path)
        if item_number is None:
            log_error(f"Could not extract Item# from filename: {layout_path}")
            return None

    log_info(f"Verifying Item# '{item_number}'...")

    # Load product data
    try:
        products_df = load_product_data(excel_path, columns=columns)
    except (FileNotFoundError, ValueError) as e:
        log_error(f"Failed to load Excel: {e}")
        return None

    # Get product
    product_data = get_product_by_item_number(products_df, item_number)
    if product_data is None:
        log_error(f"No Excel entry for Item# '{item_number}'")
        return None

    # Get fields to verify
    expected_fields = get_verification_fields(product_data)

    # Extract text from layout file
    try:
        layout_text = extract_text_from_layout(layout_path)
    except (FileNotFoundError, ValueError) as e:
        log_error(f"Failed to read layout: {e}")
        return None

    # Verify
    result = verify_product_fields(
        item_number=item_number,
        layout_file=Path(layout_path).name,
        expected_fields=expected_fields,
        layout_text=layout_text,
    )

    # Return as dict
    return {
        "item_number": result.item_number,
        "layout_file": result.layout_file,
        "total_fields": result.total_fields,
        "matched_fields": result.matched_fields,
        "missing_fields": result.missing_fields,
        "success_rate": result.success_rate,
        "is_complete": result.is_complete,
        "field_results": [
            {
                "field": fr.field_name,
                "expected": fr.expected_value,
                "found": fr.found,
                "match_type": fr.match_type,
            }
            for fr in result.field_results
        ],
    }
