# src/layout_verifier/cli.py
#
# Command-line interface for the product layout verification tool.

import argparse
import sys
import io
from pathlib import Path
from .core import verify_layouts, verify_single_product, verify_and_color_excel

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify product information consistency between Excel master data and layout files (.ai or .pdf)."
    )

    # Required arguments
    parser.add_argument(
        "--excel",
        "-e",
        required=True,
        help="Path to the Excel file containing product master data.",
    )

    # Layout input options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--layouts-dir",
        "-d",
        help="Directory containing layout files to verify.",
    )
    group.add_argument(
        "--layout",
        "-l",
        help="Path to a single layout file (.ai or .pdf) to verify.",
    )
    group.add_argument(
        "--layouts",
        "-L",
        nargs="+",
        help="List of layout files to verify (for colored Excel output).",
    )

    # Output options
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output path for the result. For --color-excel mode, this is the colored Excel file.",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "csv", "pdf", "excel"],
        default="markdown",
        help="Output format: markdown, csv, pdf, or excel (colored cells). Default: markdown.",
    )
    parser.add_argument(
        "--ext",
        "-x",
        default=".ai",
        help="File extension to scan for in --layouts-dir mode (default: .ai).",
    )
    parser.add_argument(
        "--item",
        "-i",
        default=None,
        help="Item# to verify (only used with --layout, overrides filename extraction).",
    )
    parser.add_argument(
        "--columns",
        "-C",
        nargs="+",
        default=None,
        help="Specific Excel columns to verify. If not provided, uses default columns.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("Product Layout Verification Tool")
    print("=" * 40)
    print(f"Excel file: {args.excel}")

    # Mode 1: Colored Excel output with list of layout files
    if args.layouts or args.format == "excel":
        layout_files = []

        if args.layouts:
            layout_files = args.layouts
        elif args.layouts_dir:
            # Collect files from directory
            layouts_dir = Path(args.layouts_dir)
            layout_files = [str(f) for f in layouts_dir.glob(f"*{args.ext}")]

        if not layout_files:
            print("No layout files specified or found.", file=sys.stderr)
            sys.exit(1)

        print(f"Layout files: {len(layout_files)}")
        print(f"Output format: colored Excel")
        print()

        try:
            result = verify_and_color_excel(
                layout_files=layout_files,
                excel_path=args.excel,
                output_path=args.output,
                columns=args.columns,
            )

            # Print summary
            print()
            print("=" * 40)
            print("VERIFICATION COMPLETE")
            print("=" * 40)
            print(f"Products found in layouts: {result.products_found}")
            print(f"Products not in layouts: {result.products_not_found}")
            print(f"Cells colored:")
            print(f"  - Green (matched): {result.cells_green}")
            print(f"  - Red (not matched): {result.cells_red}")
            print(f"  - Yellow (unchecked): {result.cells_yellow}")
            print()
            output_file = args.output if args.output else args.excel
            print(f"Colored Excel saved to: {output_file}")

        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(1)

    # Mode 2: Batch verification with report output
    elif args.layouts_dir:
        print(f"Layouts directory: {args.layouts_dir}")
        print(f"File extension: {args.ext}")
        print(f"Output format: {args.format}")
        if args.output:
            print(f"Output file: {args.output}")
        print()

        try:
            summary = verify_layouts(
                excel_path=args.excel,
                layouts_dir=args.layouts_dir,
                output_path=args.output,
                output_format=args.format,
                columns=args.columns,
                extension=args.ext,
            )

            # Print summary
            print()
            print("=" * 40)
            print("VERIFICATION COMPLETE")
            print("=" * 40)
            print(f"Products verified: {summary.products_verified}")
            print(f"  - Complete (all fields): {summary.products_complete}")
            print(f"  - Partial (missing fields): {summary.products_partial}")
            print(f"Layouts without Excel match: {summary.layouts_without_match}")
            print(f"Overall success rate: {summary.overall_success_rate:.1f}%")

        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(1)

    # Mode 3: Single file verification
    else:
        print(f"Layout file: {args.layout}")
        if args.item:
            print(f"Item#: {args.item}")
        print()

        result = verify_single_product(
            excel_path=args.excel,
            layout_path=args.layout,
            item_number=args.item,
            columns=args.columns,
        )

        if result is None:
            print("Verification failed. Check the error messages above.", file=sys.stderr)
            sys.exit(1)

        # Print detailed result
        print()
        print("=" * 40)
        print("VERIFICATION RESULT")
        print("=" * 40)
        print(f"Item#: {result['item_number']}")
        print(f"Layout: {result['layout_file']}")
        print(f"Fields: {result['matched_fields']}/{result['total_fields']} matched")
        print(f"Success rate: {result['success_rate']:.1f}%")
        print(f"Status: {'COMPLETE' if result['is_complete'] else 'PARTIAL'}")
        print()

        # Show field details
        print("Field Results:")
        print("-" * 40)
        for fr in result["field_results"]:
            status = "OK" if fr["found"] else "MISSING"
            match_info = f" ({fr['match_type']})" if fr["found"] else ""
            expected_display = fr['expected'][:50] + "..." if len(fr['expected']) > 50 else fr['expected']
            print(f"  [{status}] {fr['field']}: {expected_display}{match_info}")

        if not result["is_complete"]:
            sys.exit(2)  # Exit with code 2 for partial verification


if __name__ == "__main__":
    main()
