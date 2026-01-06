"""
Layout file reader for extracting text from product layout files.

Supports:
- PDF files with text (uses PyMuPDF)
- Adobe Illustrator (.ai) files (parses text from AI/PDF structure)
- Barcode extraction via pyzbar (renders page and decodes barcodes)

Note: PDFs with text converted to curves/outlines cannot be read without OCR.
For such cases, use the original .ai file which typically preserves text layers.
"""

from pathlib import Path
from typing import Generator
import re

import fitz  # PyMuPDF

from .logging_utils import log_info, log_error, log_warning


# Try to import barcode decoding library
try:
    from pyzbar import pyzbar
    from PIL import Image
    import io
    BARCODE_SUPPORT = True
except ImportError:
    BARCODE_SUPPORT = False


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    Extract all text content from a PDF file.

    Extracts text from all pages, handling rotated and positioned text.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        All extracted text concatenated as a single string.

    Raises:
        FileNotFoundError: If the PDF file doesn't exist.
        ValueError: If the file cannot be read as a PDF.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    if pdf_path.suffix.lower() not in (".pdf", ".ai"):
        raise ValueError(f"Not a PDF/AI file: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise ValueError(f"Failed to open file: {e}")

    all_text_parts = []

    for page_num, page in enumerate(doc):
        # Extract text using different methods to maximize coverage

        # Method 1: Standard text extraction
        text = page.get_text("text")
        if text:
            all_text_parts.append(text)

        # Method 2: Extract text from text blocks (handles some rotated text)
        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) >= 5 and isinstance(block[4], str):
                block_text = block[4]
                if block_text and block_text not in all_text_parts:
                    all_text_parts.append(block_text)

        # Method 3: Dictionary-based extraction for detailed text info
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if span_text:
                            all_text_parts.append(span_text)

    doc.close()

    # Combine all text parts
    combined_text = " ".join(all_text_parts)

    return combined_text


def extract_text_from_ai(ai_path: str | Path) -> str:
    """
    Extract text content from an Adobe Illustrator (.ai) file.

    AI files are typically PDF-compatible and can be read by PyMuPDF.
    They often preserve text even when the exported PDF has curves.

    Args:
        ai_path: Path to the .ai file.

    Returns:
        All extracted text concatenated as a single string.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file cannot be read.
    """
    ai_path = Path(ai_path)

    if not ai_path.exists():
        raise FileNotFoundError(f"AI file not found: {ai_path}")

    if ai_path.suffix.lower() != ".ai":
        raise ValueError(f"Not an AI file: {ai_path}")

    all_text_parts = []

    # Read AI file as PDF (AI files are PDF-compatible)
    try:
        doc = fitz.open(ai_path)
        for page in doc:
            # Standard text extraction
            text = page.get_text("text")
            if text:
                all_text_parts.append(text)

            # Dictionary extraction for additional coverage
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") == 0:
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            if span_text:
                                all_text_parts.append(span_text)
        doc.close()
    except Exception as e:
        raise ValueError(f"Could not read AI file: {e}")

    combined_text = " ".join(all_text_parts)
    return combined_text


def _extract_text_from_ai_raw(ai_path: Path) -> str:
    """
    Extract text strings from raw AI file content.

    AI files contain PostScript code where text is often encoded as:
    - Strings in parentheses: (Text here)
    - Hex strings: <48656C6C6F>
    - Text operators like Tj, TJ, '

    This function extracts readable text from these structures.
    """
    text_parts = []

    # Read file in binary mode and try to decode
    try:
        with open(ai_path, "rb") as f:
            content = f.read()
    except Exception:
        return ""

    # Try UTF-8 first, then latin-1 as fallback
    try:
        text_content = content.decode("utf-8", errors="ignore")
    except Exception:
        text_content = content.decode("latin-1", errors="ignore")

    # Pattern 1: Text in parentheses (PostScript strings)
    # Match strings like (Hello World) but handle escaped parentheses
    paren_pattern = re.compile(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)")
    for match in paren_pattern.finditer(text_content):
        text = match.group(1)
        # Unescape PostScript escape sequences
        text = _unescape_postscript_string(text)
        if text and len(text) >= 2 and _is_readable_text(text):
            text_parts.append(text)

    # Pattern 2: Look for BT...ET blocks (PDF text objects)
    bt_et_pattern = re.compile(r"BT\s*(.*?)\s*ET", re.DOTALL)
    for match in bt_et_pattern.finditer(text_content):
        block = match.group(1)
        # Extract text from Tj and TJ operators within the block
        tj_matches = re.findall(r"\(([^)]+)\)\s*Tj", block)
        for text in tj_matches:
            text = _unescape_postscript_string(text)
            if text and _is_readable_text(text):
                text_parts.append(text)

    return " ".join(text_parts)


def _unescape_postscript_string(s: str) -> str:
    """Unescape PostScript string escape sequences."""
    # Common escape sequences
    replacements = [
        (r"\\n", "\n"),
        (r"\\r", "\r"),
        (r"\\t", "\t"),
        (r"\\(", "("),
        (r"\\)", ")"),
        (r"\\\\", "\\"),
    ]
    result = s
    for old, new in replacements:
        result = result.replace(old, new)
    return result


def _is_readable_text(text: str) -> bool:
    """
    Check if extracted text is likely to be human-readable content.

    Filters out binary data, control characters, and PostScript operators.
    """
    if not text:
        return False

    # Filter out very short strings (likely not meaningful text)
    if len(text) < 2:
        return False

    # Filter out strings that are mostly non-printable
    printable_ratio = sum(1 for c in text if c.isprintable() or c.isspace()) / len(text)
    if printable_ratio < 0.8:
        return False

    # Filter out known PostScript/PDF operators
    operators = {"Tm", "Td", "Tf", "Tj", "TJ", "cm", "re", "rg", "RG", "gs", "CS", "cs"}
    if text.strip() in operators:
        return False

    return True


def extract_barcodes_from_layout(file_path: str | Path) -> list[tuple[str, str]]:
    """
    Extract barcodes from a layout file by rendering it to an image.

    Renders each page at high resolution and uses pyzbar to decode any
    barcodes (EAN-13, QR codes, etc.) present in the layout.

    Args:
        file_path: Path to the layout file (.pdf or .ai).

    Returns:
        List of (barcode_type, barcode_data) tuples for each barcode found.
        Returns empty list if pyzbar is not available or no barcodes found.
    """
    if not BARCODE_SUPPORT:
        log_warning("Barcode support not available (install pyzbar and Pillow)")
        return []

    file_path = Path(file_path)

    if not file_path.exists():
        return []

    barcodes_found = []

    try:
        doc = fitz.open(file_path)

        for page_num, page in enumerate(doc):
            # Render page at high resolution for better barcode detection
            # Using 3x zoom (216 DPI) for good quality
            mat = fitz.Matrix(3, 3)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # Decode barcodes
            decoded = pyzbar.decode(img)

            for barcode in decoded:
                barcode_type = barcode.type
                barcode_data = barcode.data.decode("utf-8", errors="ignore")
                if barcode_data:
                    barcodes_found.append((barcode_type, barcode_data))
                    log_info(f"Found {barcode_type} barcode: {barcode_data}")

        doc.close()

    except Exception as e:
        log_error(f"Error extracting barcodes from {file_path}: {e}")

    return barcodes_found


def extract_text_from_layout(file_path: str | Path, include_barcodes: bool = True) -> str:
    """
    Extract text from a layout file (PDF or AI).

    Automatically detects file type and uses appropriate extraction method.
    Optionally extracts and includes barcode data in the returned text.

    Args:
        file_path: Path to the layout file (.pdf or .ai).
        include_barcodes: If True, also extract barcodes and append their
                         data to the text. Defaults to True.

    Returns:
        Extracted text content, including barcode data if found.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file type is not supported.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".ai":
        text = extract_text_from_ai(file_path)
    elif suffix == ".pdf":
        text = extract_text_from_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}. Use .pdf or .ai files.")

    # Extract barcodes and append their data
    if include_barcodes:
        barcodes = extract_barcodes_from_layout(file_path)
        for barcode_type, barcode_data in barcodes:
            # Append barcode data to text so it can be matched during verification
            text = f"{text} {barcode_data}"

    return text


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    - Converts to lowercase
    - Collapses multiple whitespace to single space
    - Strips leading/trailing whitespace

    Args:
        text: The text to normalize.

    Returns:
        Normalized text string.
    """
    if not text:
        return ""

    # Collapse whitespace and normalize
    normalized = re.sub(r"\s+", " ", text.lower().strip())
    return normalized


def extract_item_number_from_filename(filename: str) -> str | None:
    """
    Extract the Item# from a layout filename.

    The Item# is the substring before the first space or hyphen-with-spaces in the filename.

    Args:
        filename: The layout filename (with or without path).

    Returns:
        The extracted Item#, or None if it cannot be extracted.

    Examples:
        >>> extract_item_number_from_filename("12345 Product Name.pdf")
        '12345'
        >>> extract_item_number_from_filename("199034 - FRYING PAN.ai")
        '199034'
    """
    # Get just the filename without path
    name = Path(filename).stem  # Remove extension

    # Split on first space
    parts = name.split(" ", 1)
    if parts:
        item_number = parts[0].strip()
        if item_number:
            return item_number

    return None


def scan_layout_directory(
    layouts_dir: str | Path, extension: str = ".ai"
) -> Generator[tuple[Path, str], None, None]:
    """
    Scan a directory for layout files and yield (path, item_number) pairs.

    Args:
        layouts_dir: Directory containing layout files.
        extension: File extension to look for (default: .ai).

    Yields:
        Tuples of (file_path, item_number) for each valid layout file.
    """
    layouts_dir = Path(layouts_dir)

    if not layouts_dir.exists():
        log_error(f"Layouts directory not found: {layouts_dir}")
        return

    if not layouts_dir.is_dir():
        log_error(f"Not a directory: {layouts_dir}")
        return

    pattern = f"*{extension}"
    layout_files = sorted(layouts_dir.glob(pattern))

    if not layout_files:
        log_warning(f"No {extension} files found in {layouts_dir}")
        return

    log_info(f"Found {len(layout_files)} {extension} files in {layouts_dir.name}")

    for file_path in layout_files:
        item_number = extract_item_number_from_filename(file_path.name)
        if item_number:
            yield file_path, item_number
        else:
            log_warning(f"Could not extract Item# from filename: {file_path.name}")


def get_layout_text_normalized(file_path: str | Path) -> str:
    """
    Extract and normalize text from a layout file.

    Convenience function that combines extraction and normalization.

    Args:
        file_path: Path to the layout file (.pdf or .ai).

    Returns:
        Normalized text content from the file.
    """
    raw_text = extract_text_from_layout(file_path)
    return normalize_text(raw_text)
