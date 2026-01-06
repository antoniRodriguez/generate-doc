# src/layout_verifier/config_io.py
#
# JSON config loading, output path decision and markdown saving.

import json
import os
from typing import Any, Dict, Optional


def load_project_config(path: str) -> Dict[str, Any]:
    """
    Load the JSON configuration describing the project.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Config JSON must contain a single JSON object at the root.")

    return data


def decide_output_path(
    project_info: Dict[str, Any],
    explicit_out_path: Optional[str] = None,
) -> str:
    """
    Decide where to save the Markdown output.

    If explicit_out_path is given, use it.
    Otherwise derive a filename from project_name under 'reports/'.
    """
    if explicit_out_path is not None:
        return explicit_out_path

    project_name = project_info.get("project_name", "unnamed_project")
    safe_name = "".join(
        c.lower() if c.isalnum() else "_" for c in project_name
    )
    out_dir = "reports"

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    return os.path.join(out_dir, f"{safe_name}.md")


def save_markdown(output_text: str, out_path: str) -> None:
    """
    Save the generated Markdown to disk, ensuring the directory exists.
    """
    directory = os.path.dirname(out_path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        # before writing, skip the first and last lines which are ```markdown and ``` respectively
        lines = output_text.splitlines()
        if lines and lines[0].strip() == "```markdown":
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        f.write("\n".join(lines) + "\n")