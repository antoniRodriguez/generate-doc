# src/layout_verifier/excel_colorizer.py
#
# Excel cell coloring based on verification results.
# Uses openpyxl to modify cell background colors in-place.

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from openpyxl import load_workbook
from openpyxl.styles import PatternFill

from .logging_utils import log_info, log_warning


# Color definitions (RGB hex values)
GREEN_FILL = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")  # Light green - match
RED_FILL = PatternFill(start_color="FFB6B6", end_color="FFB6B6", fill_type="solid")  # Light red - no match
YELLOW_FILL = PatternFill(start_color="FFFACD", end_color="FFFACD", fill_type="solid")  # Light yellow - unchecked
NO_FILL = PatternFill(fill_type=None)  # No background - product not found


@dataclass
class CellColorResult:
    """Tracks which cells were colored and how."""
    row: int
    column: str
    color: str  # "green", "red", "yellow", or "none"
    field_name: str
    value: str


@dataclass
class ColoringResult:
    """Summary of Excel coloring operation."""
    excel_path: str
    products_found: int
    products_not_found: int
    cells_green: int  # Matched
    cells_red: int  # Not matched
    cells_yellow: int  # Unchecked
    cell_details: list[CellColorResult]


def find_column_indices(ws, target_columns: list[str]) -> dict[str, int]:
    """
    Find column indices for target columns in the worksheet.

    Args:
        ws: openpyxl worksheet
        target_columns: List of column names to find

    Returns:
        Dictionary mapping column name to column index (1-based)
    """
    column_map = {}
    header_row = 1

    for col_idx, cell in enumerate(ws[header_row], start=1):
        if cell.value:
            cell_value = str(cell.value).strip().lower()
            for target in target_columns:
                if target.lower().strip() == cell_value:
                    column_map[target] = col_idx
                    break

    return column_map


def find_item_row(ws, item_number: str, item_col_idx: int, start_row: int = 2) -> Optional[int]:
    """
    Find the row number for a given Item#.

    Args:
        ws: openpyxl worksheet
        item_number: The Item# to find
        item_col_idx: Column index containing Item#
        start_row: Row to start searching from (default: 2, after header)

    Returns:
        Row number (1-based) or None if not found
    """
    for row_idx in range(start_row, ws.max_row + 1):
        cell_value = ws.cell(row=row_idx, column=item_col_idx).value
        if cell_value is not None:
            if str(cell_value).strip() == str(item_number).strip():
                return row_idx
    return None


def color_excel_cells(
    excel_path: str | Path,
    verification_results: dict[str, dict[str, bool]],
    output_path: Optional[str | Path] = None,
    columns_to_check: Optional[list[str]] = None,
) -> ColoringResult:
    """
    Color Excel cells based on verification results.

    Args:
        excel_path: Path to the Excel file
        verification_results: Dict mapping Item# -> {field_name: matched (bool)}
            Example: {"199034": {"EAN": True, "Name ENG": True, "Batch no:": False}}
        output_path: Where to save the colored Excel. If None, overwrites original.
        columns_to_check: List of column names to check. If None, uses all columns
                         from verification_results.

    Returns:
        ColoringResult with summary of changes made.
    """
    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    # Load workbook
    log_info(f"Loading Excel file: {excel_path.name}")
    wb = load_workbook(excel_path)
    ws = wb.active

    # Determine columns to process
    if columns_to_check is None:
        # Collect all unique field names from results
        all_fields = set()
        for fields in verification_results.values():
            all_fields.update(fields.keys())
        columns_to_check = ["Item#"] + list(all_fields)

    # Find column indices
    column_indices = find_column_indices(ws, columns_to_check)

    if "Item#" not in column_indices:
        raise ValueError("Could not find 'Item#' column in Excel file")

    item_col_idx = column_indices["Item#"]

    # Track results
    result = ColoringResult(
        excel_path=str(excel_path),
        products_found=0,
        products_not_found=0,
        cells_green=0,
        cells_red=0,
        cells_yellow=0,
        cell_details=[],
    )

    # Process each item in verification results
    items_processed = set()
    for item_number, field_results in verification_results.items():
        row_idx = find_item_row(ws, item_number, item_col_idx)

        if row_idx is None:
            log_warning(f"Item# '{item_number}' not found in Excel")
            result.products_not_found += 1
            continue

        result.products_found += 1
        items_processed.add(item_number)

        # Color each field cell for this product
        for field_name, matched in field_results.items():
            if field_name not in column_indices:
                continue

            col_idx = column_indices[field_name]
            cell = ws.cell(row=row_idx, column=col_idx)
            cell_value = str(cell.value) if cell.value else ""

            if matched:
                cell.fill = GREEN_FILL
                result.cells_green += 1
                color = "green"
            else:
                cell.fill = RED_FILL
                result.cells_red += 1
                color = "red"

            result.cell_details.append(CellColorResult(
                row=row_idx,
                column=field_name,
                color=color,
                field_name=field_name,
                value=cell_value[:50] if cell_value else "",
            ))

        # Color unchecked columns (columns we have in Excel but weren't verified)
        for col_name, col_idx in column_indices.items():
            if col_name == "Item#":
                continue
            if col_name not in field_results:
                cell = ws.cell(row=row_idx, column=col_idx)
                # Only color if cell has a value
                if cell.value:
                    cell.fill = YELLOW_FILL
                    result.cells_yellow += 1
                    result.cell_details.append(CellColorResult(
                        row=row_idx,
                        column=col_name,
                        color="yellow",
                        field_name=col_name,
                        value=str(cell.value)[:50] if cell.value else "",
                    ))

    # Save workbook
    save_path = Path(output_path) if output_path else excel_path
    log_info(f"Saving colored Excel to: {save_path.name}")
    wb.save(save_path)
    wb.close()

    log_info(f"Colored {result.cells_green} green, {result.cells_red} red, {result.cells_yellow} yellow cells")

    return result
