"""
Excel reader for product master data.

Reads product information from an Excel file where each row represents a product
and columns contain product attributes like Item#, EAN, descriptions, etc.
"""

from pathlib import Path
import pandas as pd
from typing import Optional

from .logging_utils import log_info, log_error, log_warning


# Default columns of interest for product verification
# Note: "Seria" and "type of packaging" are often rendered as images or not on the box
# EAN is verified via barcode extraction from the layout
DEFAULT_COLUMNS = [
    "Item#",
    "EAN",
    "Name ENG",
    "Name in all our languages",
    "address under EAN/barcode",
    "origin (next to EAN/barcode)",
    "Batch no:",
]


def load_product_data(
    excel_path: str | Path,
    sheet_name: str | int = 0,
    columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Load product data from an Excel file.

    Args:
        excel_path: Path to the Excel file containing product data.
        sheet_name: Name or index of the worksheet to read (default: first sheet).
        columns: List of column names to extract. If None, uses DEFAULT_COLUMNS.
                 Only columns that exist in the Excel file will be returned.

    Returns:
        DataFrame with product data, indexed by Item# if that column exists.

    Raises:
        FileNotFoundError: If the Excel file doesn't exist.
        ValueError: If the Excel file cannot be read or has no valid data.
    """
    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    if not excel_path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
        raise ValueError(f"Not a valid Excel file: {excel_path}")

    log_info(f"Loading product data from: {excel_path.name}")

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}")

    if df.empty:
        raise ValueError("Excel file contains no data")

    # Determine which columns to use
    target_columns = columns if columns is not None else DEFAULT_COLUMNS

    # Find columns that exist in the dataframe (case-insensitive matching)
    df_columns_lower = {col.lower().strip(): col for col in df.columns}
    available_columns = []
    column_mapping = {}

    for col in target_columns:
        col_lower = col.lower().strip()
        if col_lower in df_columns_lower:
            original_col = df_columns_lower[col_lower]
            available_columns.append(original_col)
            column_mapping[original_col] = col

    if not available_columns:
        raise ValueError(
            f"None of the expected columns found in Excel. "
            f"Expected: {target_columns}, Found: {list(df.columns)}"
        )

    # Report missing columns
    missing = set(c.lower().strip() for c in target_columns) - set(
        c.lower().strip() for c in available_columns
    )
    if missing:
        log_warning(f"Some columns not found in Excel: {missing}")

    # Select and rename columns to standardized names
    result_df = df[available_columns].copy()
    result_df.columns = [column_mapping[col] for col in available_columns]

    # Ensure Item# column exists for indexing
    if "Item#" in result_df.columns:
        # Convert Item# to string and strip whitespace
        result_df["Item#"] = result_df["Item#"].astype(str).str.strip()
        # Remove rows with empty Item#
        result_df = result_df[result_df["Item#"].notna() & (result_df["Item#"] != "")]
        result_df = result_df[result_df["Item#"] != "nan"]

    log_info(f"Loaded {len(result_df)} products with {len(result_df.columns)} columns")

    return result_df


def get_product_by_item_number(df: pd.DataFrame, item_number: str) -> Optional[dict]:
    """
    Get a single product's data by its Item#.

    Args:
        df: DataFrame with product data (must have 'Item#' column).
        item_number: The item number to look up.

    Returns:
        Dictionary of column_name -> value for the product, or None if not found.
    """
    if "Item#" not in df.columns:
        log_error("DataFrame does not have 'Item#' column")
        return None

    item_number = str(item_number).strip()
    matches = df[df["Item#"] == item_number]

    if matches.empty:
        return None

    if len(matches) > 1:
        log_warning(f"Multiple products found with Item# '{item_number}', using first")

    return matches.iloc[0].to_dict()


def get_verification_fields(product_data: dict) -> dict[str, str]:
    """
    Extract fields that need to be verified from product data.

    Filters out empty values and returns only non-empty fields for verification.

    Args:
        product_data: Dictionary of product attributes.

    Returns:
        Dictionary of field_name -> value for non-empty fields.
    """
    verification_fields = {}

    for key, value in product_data.items():
        if key == "Item#":
            # Item# is used for matching, not verification
            continue

        # Convert to string and check if non-empty
        str_value = str(value).strip() if pd.notna(value) else ""
        if str_value and str_value.lower() != "nan":
            verification_fields[key] = str_value

    return verification_fields
