# src/docgen/core.py
#
# High-level orchestration:
# - Load config
# - Extract dataset info (YOLO-style) if dataset_root is provided
# - Extract metrics info from Excel if metrics_path is provided
# - Extract ONNX technical info if model_path is provided
# - Build prompt (including dataset, metrics, and ONNX summaries when available)
# - Detect GPU and print hints
# - Show spinner while calling the LLM
# - Save Markdown report
# - Save PDF report (optional)
from typing import Optional, Dict, Any

from ollama import chat, ChatResponse

from .config_io import load_project_config, decide_output_path, save_markdown
from .hardware import detect_gpu, infer_model_size_label, print_gpu_and_model_hint
from .prompt_builder import SYSTEM_PROMPT, build_user_prompt
from .spinner import Spinner
from .logging_utils import log_info, log_llm, log_warning
from .dataset_info import extract_dataset_info
from .metrics_info import extract_metrics_info
from .onnx_info import extract_onnx_info
from .pdf_writer import save_pdf_from_markdown


DEFAULT_MODEL_NAME = "deepseek-r1:8b"


def generate_documentation(
    config_path: str,
    model_name: Optional[str] = None,
    out_path: Optional[str] = None,
) -> str:
    """
    High-level function that:
    - loads the project JSON
    - extracts dataset information (if dataset_root is provided)
    - extracts metrics information from Excel (if metrics_path is provided)
    - extracts ONNX model information (if model_path is provided)
    - builds the LLM prompt
    - detects GPU and prints hints
    - shows a spinner while calling the DeepSeek model via Ollama
    - saves the Markdown report

    Returns the output path used.
    """

    if model_name is None:
        model_name = DEFAULT_MODEL_NAME

    # 1) Load config
    log_info(f"Loading project configuration from '{config_path}'...")
    project_info: Dict[str, Any] = load_project_config(config_path)
    log_info("Configuration loaded successfully. ✔")

    # 2) Extract dataset info (if dataset_root present)
    dataset_info: Optional[Dict[str, Any]] = None
    dataset_root = project_info.get("dataset_root")

    if isinstance(dataset_root, str) and dataset_root.strip():
        log_info(f"Extracting dataset information from '{dataset_root}'...")
        dataset_info = extract_dataset_info(dataset_root)
        log_info("Dataset information extracted. ✔")
    else:
        log_warning(
            "No 'dataset_root' provided in config or it is empty; "
            "skipping dataset analysis."
        )

    # 3) Extract metrics info (if metrics_path present)
    metrics_info: Optional[Dict[str, Any]] = None
    metrics_path = project_info.get("metrics_path")

    if isinstance(metrics_path, str) and metrics_path.strip():
        log_info(f"Extracting metrics information from '{metrics_path}'...")
        metrics_info = extract_metrics_info(metrics_path)
        log_info("Metrics information extracted. ✔")
    else:
        log_warning(
            "No 'metrics_path' provided in config or it is empty; "
            "skipping metrics analysis."
        )

    # 4) Extract ONNX info (if model_path present)
    onnx_info: Optional[Dict[str, Any]] = None
    model_path = project_info.get("model_path")

    if isinstance(model_path, str) and model_path.strip():
        log_info(f"Extracting ONNX model information from '{model_path}'...")
        onnx_info = extract_onnx_info(model_path)
        log_info("ONNX model information extracted. ✔")
    else:
        log_warning(
            "No 'model_path' provided in config or it is empty; "
            "skipping ONNX model analysis."
        )

    # 5) Build prompt (project info + optional dataset + optional metrics + optional ONNX)
    log_info("Building prompt for the documentation...")
    user_prompt = build_user_prompt(
        project_info,
        dataset_info=dataset_info,
        metrics_info=metrics_info,
        onnx_info=onnx_info,
    )
    log_info("Prompt built. ✔")

    # 6) Decide output path
    output_md_path = decide_output_path(project_info, out_path)
    log_info(f"Documentation will be saved to '{output_md_path}'.")

    # 7) GPU + model hints
    gpu_info = detect_gpu()
    model_size_label = infer_model_size_label(model_name)
    print_gpu_and_model_hint(gpu_info, model_name, model_size_label)

    # 8) Spinner during LLM call
    spinner = Spinner("Generating documentation...")
    log_llm("Sending prompt to the model.")
    spinner.start()
    try:
        response: ChatResponse = chat(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    finally:
        spinner.stop()

    log_llm("Generation complete. ✔")

    # 9) Save Markdown + optional PDF
    doc_text = response.message.content
    log_info("Saving documentation...")

    formats = project_info.get("output_format", ["markdown"])

    if "markdown" in formats:
        save_markdown(doc_text, output_md_path)
        log_info("Markdown saved. ✔")

    if "pdf" in formats:
        pdf_path = output_md_path.replace(".md", ".pdf")
        save_pdf_from_markdown(doc_text, pdf_path)
        log_info(f"PDF saved to '{pdf_path}'. ✔")

    log_info("All requested formats saved successfully.")
