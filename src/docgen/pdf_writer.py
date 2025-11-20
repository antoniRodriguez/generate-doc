# src/docgen/pdf_writer.py
#
# Markdown → PDF conversion using pure Python libraries:
# - markdown: Markdown → HTML
# - xhtml2pdf: HTML → PDF
#
# This works on Windows without external binaries like wkhtmltopdf.

import os
from markdown import markdown
from xhtml2pdf import pisa

from .logging_utils import log_info, log_error


def _strip_wrapping_markdown_fence(markdown_text: str) -> str:
    """
    If the entire content is wrapped in a top-level fenced code block like:

        ```markdown
        ...
        ```

    remove the outer fences so we render the inner Markdown instead of a big code block.
    """
    lines = markdown_text.splitlines()

    if lines and lines[0].strip() == "```markdown":
        lines = lines[1:]
    if lines and lines and lines[0].strip() == "```":  # handle plain ``` as first line
        lines = lines[1:]

    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines)


def save_pdf_from_markdown(markdown_text: str, output_path: str) -> None:
    """
    Convert Markdown → HTML → PDF using xhtml2pdf.

    Raises RuntimeError if PDF generation fails.
    """
    # Remove outer ```markdown ... ``` (or ``` ... ```) if present
    cleaned_markdown = _strip_wrapping_markdown_fence(markdown_text)

    # Basic GitHub-style HTML from Markdown
    body_html = markdown(
        cleaned_markdown,
        extensions=["fenced_code", "tables"]
    )

    # Simple styling to keep the PDF readable and professional
    full_html = f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>
          body {{
            font-family: DejaVu Sans, Arial, Helvetica, sans-serif;
            font-size: 11pt;
            line-height: 1.4;
          }}
          h1, h2, h3, h4 {{
            font-weight: bold;
            margin-top: 12px;
            margin-bottom: 6px;
          }}
          h1 {{
            font-size: 18pt;
          }}
          h2 {{
            font-size: 14pt;
          }}
          h3 {{
            font-size: 12pt;
          }}
          p {{
            margin: 4px 0;
          }}
          code, pre {{
            font-family: "DejaVu Sans Mono", Consolas, monospace;
            font-size: 9pt;
          }}
          pre {{
            background: #f5f5f5;
            padding: 6px;
            border-radius: 4px;
            overflow-x: auto;
          }}
          table {{
            border-collapse: collapse;
            width: 100%;
            margin: 6px 0;
          }}
          th, td {{
            border: 1px solid #cccccc;
            padding: 4px 6px;
            font-size: 9pt;
          }}
          th {{
            background: #eeeeee;
          }}
        </style>
      </head>
      <body>
        {body_html}
      </body>
    </html>
    """

    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    log_info(f"Generating PDF at '{output_path}'...")

    with open(output_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(full_html, dest=pdf_file)

    if pisa_status.err:
        log_error(f"PDF generation failed for '{output_path}'.")
        raise RuntimeError("PDF generation failed (xhtml2pdf reported errors).")

    log_info(f"PDF successfully generated at '{output_path}' ✔")
