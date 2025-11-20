# model-docgen

Local documentation generator for internal computer vision / deep learning projects.  
It runs a local DeepSeek model via Ollama, inspects your dataset, metrics and ONNX model, and produces a Markdown report.

---

## 1. Introduction

This utility is meant to be a small internal tool, not a framework.

Given a JSON config, it:
- Reads basic project info (name, type, notes).
- Analyses a YOLO-style dataset (images, labels, classes).
- Reads metrics from an Excel file.
- Inspects an ONNX model (inputs, outputs, parameter count).
- Sends a structured prompt to a local DeepSeek model.
- Saves a Markdown document with a professional, wiki-style structure.

---

## 2. What this is

- A command-line tool: you run `generate-doc --config config.json`.
- Model-agnostic on the ML side: it just reads dataset, metrics and ONNX.
- Opinionated on structure: project types like license plate detection, character detection, and vehicle detection have internal templates and descriptions that guide the generated documentation.

It is not:
- A training pipeline.
- A deployment tool.
- A replacement for your experiment tracking.

---

## 3. Requirements

- Python 3.10+
- Ollama installed on your machine
- A local DeepSeek model available in Ollama (by default: `deepseek-r1:8b`)

---

## 4. Setup

1. **Install Ollama for Windows**

   Download and install from:  
   https://ollama.com/download/windows

2. **Pull the DeepSeek model**

       ollama pull deepseek-r1:8b

3. **Create a Python virtual environment (optional but recommended)**

   In the project root:

       python -m venv venv

   Activate it:

   - WSL / bash:

         source venv/Scripts/activate

   - PowerShell:

         .\venv\Scripts\activate

4. **Install the project in editable mode**

   From the project root (where `pyproject.toml` lives):

       pip install -e .

---

## 5. Configuration

The tool expects a JSON config file with the main paths and metadata.  
Example:

    {
      "project_name": "<PROJECT NAME>",
      "project_type": "<PROJECT TYPE>",
      "model_path": "model.onnx",
      "dataset_root": "path to yolo dataset root folder",
      "metrics_path": "path to metrics file",
      "notes": "Additional information",
      "output_format": ["markdown"]
    }

Key fields:

- `project_name`  
  Used as the main title of the generated document.

- `project_type`  
  Used to load internal descriptions and recommended sections.  
  Currently supported:
  - `license_plate_detection`
  - `character_detection`
  - `vehicle_detection`

- `model_path`  
  Path to the ONNX model. Used to extract:
  - Inputs (names, dtypes, shapes)
  - Outputs (names, dtypes, shapes)
  - Approximate number of parameters

- `dataset_root`  
  Root of a YOLO-style dataset:
  - `images/`
  - `labels/`
  - `classes.txt`  
  Used to compute:
  - Number of images
  - Number of objects
  - Per-class object counts

- `metrics_path`  
  Excel file with a worksheet named `raw-results` and rows by class plus an `all` row.  
  Used to include a concise performance summary.

- `notes`  
  Free text that is passed to the model as additional context.

- `output_format`  
  Currently expected to contain `"markdown"`. In the PoC this simply means it writes a `*.md` file.

---

## 6. Usage

From the project root:

    generate-doc --config path/to/config.json

What happens:

1. The tool loads the config.
2. If `dataset_root` is set:
   - Counts images and label files.
   - Computes per-class object counts based on YOLO labels.
3. If `metrics_path` is set:
   - Reads the `raw-results` sheet from the Excel file.
   - Extracts per-class metrics and the aggregated `all` row.
4. If `model_path` is set:
   - Loads the ONNX model.
   - Extracts input/output tensors and parameter count.
5. Looks up the project type (`license_plate_detection`, `character_detection`, `vehicle_detection`) and adds the corresponding internal description and recommended sections.
6. Builds a structured prompt and sends it to the local DeepSeek model via Ollama.
7. Saves the generated Markdown file in the `reports/` folder (by default).

---

## 7. Logic (technical overview)

High-level structure:

- `docgen/core.py`  
  Orchestrates the flow: config → dataset/metrics/onnx info → prompt → LLM → Markdown.

- `docgen/dataset_info.py`  
  Analyses YOLO datasets:
  - Counts images.
  - Counts objects per class using `labels/` and `classes.txt`.

- `docgen/metrics_info.py`  
  Reads an Excel workbook (sheet `raw-results`) and extracts:
  - Per-class metrics (Precision, Recall, F1, AP@0.5, GT, TP, FP, FN, Wrong Class).
  - A global `all` row.

- `docgen/onnx_info.py`  
  Loads an ONNX model and extracts:
  - Input / output tensor names, dtypes and shapes.
  - Approximate number of parameters.

- `docgen/project_types.py`  
  Contains internal templates for:
  - License plate detection
  - Character detection
  - Vehicle detection  
  Each template includes a textual task description, data notes and recommended sections.

- `docgen/prompt_builder.py`  
  Assembles a single user prompt string containing:
  - Project metadata
  - Project-type details
  - Dataset summary
  - Metrics summary
  - ONNX technical summary  
  This prompt is passed to the DeepSeek model.

- `docgen/logging_utils.py` and `docgen/spinner.py`  
  Provide colored logs and a small spinner while the LLM is generating the document, so the user sees that the tool is alive.

---

## 8. Notes and limitations

- Assumes datasets follow a simple YOLO layout; other structures are not handled.
- Assumes metrics Excel has a `raw-results` sheet with a `Class` column and an `all` row.
- Assumes the model is in ONNX format; other model formats are not inspected.
- The tool does not perform any training or evaluation; it only reads existing artefacts and generates documentation.
