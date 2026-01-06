"""
String matching and verification logic for product layout verification.

Checks that expected product fields exist in layout text, handling
various matching strategies (exact, normalized, fuzzy).
"""

from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class FieldResult:
    """Result of verifying a single field."""

    field_name: str
    expected_value: str
    found: bool
    match_type: str = ""  # "exact", "normalized", "partial", "not_found"
    matched_text: str = ""


@dataclass
class ProductVerificationResult:
    """Result of verifying all fields for a single product."""

    item_number: str
    layout_file: str
    total_fields: int = 0
    matched_fields: int = 0
    missing_fields: int = 0
    field_results: list[FieldResult] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Percentage of fields that were found."""
        if self.total_fields == 0:
            return 0.0
        return (self.matched_fields / self.total_fields) * 100

    @property
    def is_complete(self) -> bool:
        """Whether all expected fields were found."""
        return self.missing_fields == 0


def normalize_for_matching(text: str) -> str:
    """
    Normalize text for comparison.

    - Convert to lowercase
    - Collapse whitespace
    - Remove common punctuation variations
    """
    if not text:
        return ""

    # Lowercase and strip
    result = text.lower().strip()

    # Collapse whitespace
    result = re.sub(r"\s+", " ", result)

    return result


def find_value_in_text(
    expected_value: str,
    layout_text: str,
    layout_text_normalized: Optional[str] = None,
) -> tuple[bool, str, str]:
    """
    Check if an expected value exists in the layout text.

    Tries multiple matching strategies in order:
    1. Exact match (case-sensitive)
    2. Normalized match (case-insensitive, whitespace-collapsed)
    3. Partial/substring match for multi-word values

    Args:
        expected_value: The value to find.
        layout_text: The raw layout text.
        layout_text_normalized: Pre-normalized layout text (optional, for efficiency).

    Returns:
        Tuple of (found, match_type, matched_text).
    """
    if not expected_value or not layout_text:
        return False, "not_found", ""

    expected_stripped = expected_value.strip()

    # Strategy 1: Exact match
    if expected_stripped in layout_text:
        return True, "exact", expected_stripped

    # Strategy 2: Normalized match
    expected_normalized = normalize_for_matching(expected_stripped)
    if layout_text_normalized is None:
        layout_text_normalized = normalize_for_matching(layout_text)

    if expected_normalized in layout_text_normalized:
        return True, "normalized", expected_normalized

    # Strategy 3: For multi-word values, check if all words are present
    # (handles cases where words might be on different lines/positions)
    words = expected_normalized.split()
    if len(words) > 1:
        all_words_found = all(word in layout_text_normalized for word in words)
        if all_words_found:
            return True, "partial", f"all words found: {words}"

    # Strategy 4: For numeric values (like EAN), try variations
    # Remove common separators and check
    if expected_stripped.replace("-", "").replace(" ", "").isdigit():
        clean_expected = expected_stripped.replace("-", "").replace(" ", "")
        clean_layout = re.sub(r"[\s\-]", "", layout_text_normalized)
        if clean_expected.lower() in clean_layout:
            return True, "normalized", clean_expected

    return False, "not_found", ""


def verify_product_fields(
    item_number: str,
    layout_file: str,
    expected_fields: dict[str, str],
    layout_text: str,
) -> ProductVerificationResult:
    """
    Verify that all expected fields exist in the layout text.

    Args:
        item_number: The product's Item# identifier.
        layout_file: Name of the layout file being verified.
        expected_fields: Dictionary of field_name -> expected_value.
        layout_text: The extracted text from the layout file.

    Returns:
        ProductVerificationResult with details about each field's verification.
    """
    result = ProductVerificationResult(
        item_number=item_number,
        layout_file=layout_file,
        total_fields=len(expected_fields),
    )

    # Pre-normalize layout text for efficiency
    layout_normalized = normalize_for_matching(layout_text)

    for field_name, expected_value in expected_fields.items():
        found, match_type, matched_text = find_value_in_text(
            expected_value, layout_text, layout_normalized
        )

        field_result = FieldResult(
            field_name=field_name,
            expected_value=expected_value,
            found=found,
            match_type=match_type,
            matched_text=matched_text,
        )

        result.field_results.append(field_result)

        if found:
            result.matched_fields += 1
        else:
            result.missing_fields += 1

    return result


@dataclass
class VerificationSummary:
    """Summary of verification across all products."""

    total_products: int = 0
    products_verified: int = 0
    products_complete: int = 0  # All fields found
    products_partial: int = 0  # Some fields missing
    products_not_found: int = 0  # No matching Excel row
    layouts_without_match: int = 0  # Layout files with no Excel match
    results: list[ProductVerificationResult] = field(default_factory=list)
    unmatched_layouts: list[str] = field(default_factory=list)

    @property
    def overall_success_rate(self) -> float:
        """Percentage of products with all fields verified."""
        if self.products_verified == 0:
            return 0.0
        return (self.products_complete / self.products_verified) * 100

    def add_result(self, result: ProductVerificationResult):
        """Add a verification result and update counts."""
        self.results.append(result)
        self.products_verified += 1
        if result.is_complete:
            self.products_complete += 1
        else:
            self.products_partial += 1

    def add_unmatched_layout(self, filename: str):
        """Record a layout file that had no matching Excel entry."""
        self.unmatched_layouts.append(filename)
        self.layouts_without_match += 1
