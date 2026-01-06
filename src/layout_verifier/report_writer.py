"""
Report generation for product layout verification results.

Generates verification reports in multiple formats:
- Markdown (human-readable)
- CSV (for further processing)
- PDF (via markdown conversion)
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .verifier import VerificationSummary

from .pdf_writer import save_pdf_from_markdown


def generate_report(summary: "VerificationSummary", output_format: str = "markdown") -> str:
    """
    Generate a verification report from the summary.

    Args:
        summary: VerificationSummary with all verification results.
        output_format: Output format - "markdown", "csv", or "pdf".

    Returns:
        Report content as a string.
    """
    if output_format == "csv":
        return _generate_csv_report(summary)
    else:
        # Markdown (also used as base for PDF)
        return _generate_markdown_report(summary)


def _generate_markdown_report(summary: "VerificationSummary") -> str:
    """Generate a Markdown verification report."""
    lines = []

    # Header
    lines.append("# Product Layout Verification Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Summary section
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total products in Excel:** {summary.total_products}")
    lines.append(f"- **Layouts verified:** {summary.products_verified}")
    lines.append(f"- **Fully verified (all fields found):** {summary.products_complete}")
    lines.append(f"- **Partially verified (some fields missing):** {summary.products_partial}")
    lines.append(f"- **Layouts without Excel match:** {summary.layouts_without_match}")
    lines.append(f"- **Overall success rate:** {summary.overall_success_rate:.1f}%")
    lines.append("")

    # Unmatched layouts
    if summary.unmatched_layouts:
        lines.append("## Layouts Without Excel Match")
        lines.append("")
        lines.append("The following layout files could not be matched to any product in Excel:")
        lines.append("")
        for filename in summary.unmatched_layouts:
            lines.append(f"- {filename}")
        lines.append("")

    # Products with missing fields
    products_with_issues = [r for r in summary.results if not r.is_complete]
    if products_with_issues:
        lines.append("## Products With Missing Fields")
        lines.append("")

        for result in products_with_issues:
            lines.append(f"### Item# {result.item_number}")
            lines.append(f"**File:** {result.layout_file}")
            lines.append(f"**Match rate:** {result.success_rate:.1f}% ({result.matched_fields}/{result.total_fields})")
            lines.append("")

            # Show missing fields
            missing = [fr for fr in result.field_results if not fr.found]
            if missing:
                lines.append("**Missing fields:**")
                lines.append("")
                lines.append("| Field | Expected Value |")
                lines.append("|-------|----------------|")
                for fr in missing:
                    # Escape pipe characters in values
                    expected = fr.expected_value.replace("|", "\\|")
                    lines.append(f"| {fr.field_name} | {expected} |")
                lines.append("")

            # Show found fields
            found = [fr for fr in result.field_results if fr.found]
            if found:
                lines.append("**Found fields:**")
                lines.append("")
                lines.append("| Field | Value | Match Type |")
                lines.append("|-------|-------|------------|")
                for fr in found:
                    value = fr.expected_value.replace("|", "\\|")
                    lines.append(f"| {fr.field_name} | {value} | {fr.match_type} |")
                lines.append("")

    # Fully verified products (brief list)
    complete_products = [r for r in summary.results if r.is_complete]
    if complete_products:
        lines.append("## Fully Verified Products")
        lines.append("")
        lines.append("The following products have all fields verified:")
        lines.append("")
        lines.append("| Item# | Layout File | Fields |")
        lines.append("|-------|-------------|--------|")
        for result in complete_products:
            lines.append(f"| {result.item_number} | {result.layout_file} | {result.total_fields} |")
        lines.append("")

    return "\n".join(lines)


def _generate_csv_report(summary: "VerificationSummary") -> str:
    """Generate a CSV verification report."""
    lines = []

    # Header
    lines.append("Item#,Layout File,Total Fields,Matched,Missing,Success Rate,Status,Missing Fields")

    for result in summary.results:
        missing_fields = [fr.field_name for fr in result.field_results if not fr.found]
        missing_str = "; ".join(missing_fields) if missing_fields else ""

        status = "COMPLETE" if result.is_complete else "PARTIAL"

        # Escape commas in filename and missing fields
        layout_file = f'"{result.layout_file}"' if "," in result.layout_file else result.layout_file
        missing_str = f'"{missing_str}"' if "," in missing_str or ";" in missing_str else missing_str

        lines.append(
            f"{result.item_number},{layout_file},{result.total_fields},"
            f"{result.matched_fields},{result.missing_fields},{result.success_rate:.1f}%,"
            f"{status},{missing_str}"
        )

    # Add unmatched layouts at the end
    for filename in summary.unmatched_layouts:
        layout_file = f'"{filename}"' if "," in filename else filename
        lines.append(f"N/A,{layout_file},0,0,0,0%,NO_MATCH,")

    return "\n".join(lines)


def save_report(content: str, output_path: str, output_format: str = "markdown"):
    """
    Save the report to a file.

    Args:
        content: Report content string.
        output_path: Path to save the report.
        output_format: Format - "markdown", "csv", or "pdf".
    """
    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "pdf":
        # Use the pdf_writer module for PDF generation
        save_pdf_from_markdown(content, str(output_path))
    else:
        # Text-based formats (markdown, csv)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
