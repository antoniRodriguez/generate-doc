# src/docgen/metrics_info.py
#
# Utilities to extract model metrics from an Excel file.
#
# The Excel file is expected to have a worksheet named 'raw-results'
# with a table of the form:
#
# Class    Precision   Recall  F1  AP@0.5  GT  TP  FP  FN  Wrong Class   conf
# Mercosur ...
# Old      ...
# all      ...
#
# Each row represents metrics for one class, plus a special row "all"
# which accumulates metrics across classes.

from typing import Any, Dict, List

import pandas as pd

from .logging_utils import log_info, log_warning, log_error


EXPECTED_SHEET_NAME = "raw-results"
CLASS_COLUMN = "Class"


def extract_metrics_info(excel_path: str) -> Dict[str, Any]:
    """
    Read metrics from an Excel file and return a structured dict.

    Returns a dictionary with keys:
        - 'metrics_path': str
        - 'sheet_name': str
        - 'per_class': Dict[str, Dict[str, Any]]   # class_name -> metrics row
        - 'summary_all': Dict[str, Any] or None   # metrics row for "all"
        - 'classes': List[str]                    # list of class names (excluding "all")
    """
    info: Dict[str, Any] = {
        "metrics_path": excel_path,
        "sheet_name": EXPECTED_SHEET_NAME,
        "per_class": {},
        "summary_all": None,
        "classes": [],
    }

    try:
        df = pd.read_excel(excel_path, sheet_name=EXPECTED_SHEET_NAME)
    except FileNotFoundError:
        log_error(f"Metrics Excel file not found at '{excel_path}'.")
        return info
    except ValueError as ex:
        # e.g. sheet not found
        log_error(
            f"Could not read sheet '{EXPECTED_SHEET_NAME}' from '{excel_path}': {ex}"
        )
        return info
    except Exception as ex:
        log_error(f"Error reading metrics Excel file '{excel_path}': {ex}")
        return info

    if CLASS_COLUMN not in df.columns:
        log_error(
            f"Expected a '{CLASS_COLUMN}' column in the '{EXPECTED_SHEET_NAME}' sheet "
            f"of '{excel_path}', but it was not found."
        )
        return info

    # Drop fully empty rows if any
    df = df.dropna(how="all")

    per_class: Dict[str, Dict[str, Any]] = {}
    summary_all: Dict[str, Any] | None = None
    classes: List[str] = []

    for _, row in df.iterrows():
        class_name_raw = row.get(CLASS_COLUMN)
        if class_name_raw is None:
            continue

        class_name = str(class_name_raw).strip()
        if not class_name:
            continue

        # Convert the row to a plain dict, but skip NaN where possible
        metrics_row: Dict[str, Any] = {}
        for col in df.columns:
            value = row[col]
            # Replace pandas NaN with None for cleaner downstream usage
            if isinstance(value, float) and pd.isna(value):
                metrics_row[col] = None
            else:
                metrics_row[col] = value

        if class_name.lower() == "all":
            summary_all = metrics_row
        else:
            per_class[class_name] = metrics_row
            classes.append(class_name)

    info["per_class"] = per_class
    info["summary_all"] = summary_all
    info["classes"] = classes

    log_info(
        f"Metrics summary loaded from '{excel_path}' "
        f"(sheet '{EXPECTED_SHEET_NAME}')."
    )
    if classes:
        log_info(
            "Per-class metrics available for: " + ", ".join(classes)
        )
    if summary_all is None:
        log_warning(
            "No 'all' row found in metrics (Class == 'all'); "
            "global summary will not be available."
        )

    return info
