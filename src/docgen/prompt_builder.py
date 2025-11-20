# src/docgen/prompt_builder.py
#
# System prompt and user prompt construction.

from typing import Any, Dict, List, Optional

from .project_types import get_project_type_info


SYSTEM_PROMPT = (
    "You are an internal technical documentation assistant for a computer "
    "vision and deep learning company.\n\n"
    "Your job is to generate clear, concise and professional documentation "
    "for internal projects.\n\n"
    "Requirements:\n"
    "- Write in English with a professional but readable tone.\n"
    "- Use GitHub-flavoured Markdown (headings, bullet lists, tables when useful).\n"
    "- Do not invent technical details. If something is not provided, say 'Not specified'.\n"
    "- Organise the document into logical sections like: Overview, Model, Dataset, "
    "Training and Augmentations (if applicable), Deployment / Usage (if mentioned), "
    "Limitations and Notes.\n"
    "- Make the text suitable for an internal wiki.\n"
)


def build_user_prompt(
    project_info: Dict[str, Any],
    dataset_info: Optional[Dict[str, Any]] = None,
    metrics_info: Optional[Dict[str, Any]] = None,
    onnx_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Build the user prompt given:
    - project_info loaded from JSON
    - optional dataset_info extracted from a YOLO dataset
    - optional metrics_info extracted from an Excel file
    - optional onnx_info extracted from an ONNX model
    """
    project_name = project_info.get("project_name", "Unnamed project")
    project_type_raw = project_info.get("project_type", "Not specified")
    model_path = project_info.get("model_path", "Not specified")
    dataset_root = project_info.get("dataset_root", "Not specified")
    metrics_path = project_info.get("metrics_path", "Not specified")
    notes = project_info.get("notes", "Not specified")

    lines: List[str] = []

    lines.append(
        "Generate a well-structured internal documentation page in Markdown "
        "for the following deep learning project."
    )
    lines.append("")
    lines.append("Project information (as provided):")
    lines.append("")
    lines.append(f"- Project name: {project_name}")
    lines.append(f"- Project type (raw): {project_type_raw}")
    lines.append(f"- Model path: {model_path}")
    lines.append(f"- Dataset root: {dataset_root}")
    lines.append(f"- Metrics Excel path: {metrics_path}")
    lines.append(f"- Notes: {notes}")
    lines.append("")

    # ----------------------------------------------------------------------
    # Project type details (from internal config)
    # ----------------------------------------------------------------------
    canonical_type, type_cfg = get_project_type_info(str(project_type_raw))

    if type_cfg is not None:
        display_name = type_cfg.get("display_name", canonical_type or "Unknown")
        description = type_cfg.get("description", "")
        data_notes = type_cfg.get("data_notes", "")
        recommended_sections = type_cfg.get("recommended_sections", [])

        lines.append("Project type details (internal config):")
        lines.append("")
        lines.append(f"- Canonical type: {display_name}")
        if description:
            lines.append(f"- Task description: {description}")
        if data_notes:
            lines.append(f"- Data characteristics: {data_notes}")
        if recommended_sections:
            lines.append("")
            lines.append("Recommended sections for the documentation:")
            for sec in recommended_sections:
                lines.append(f"  - {sec}")
        lines.append("")
    else:
        lines.append(
            "Project type details: The provided project_type does not match any known "
            "internal project type configuration. Use a generic object detection "
            "documentation structure."
        )
        lines.append("")

    # ----------------------------------------------------------------------
    # Dataset section
    # ----------------------------------------------------------------------
    if dataset_info is not None:
        num_images = dataset_info.get("num_images", "Not specified")
        num_objects = dataset_info.get("num_objects", "Not specified")
        classes = dataset_info.get("classes", [])
        class_counts_by_name = dataset_info.get("class_counts_by_name", {})

        lines.append("Dataset summary (automatically extracted):")
        lines.append("")
        lines.append(f"- Number of images: {num_images}")
        lines.append(f"- Number of annotated objects: {num_objects}")
        lines.append(f"- Number of classes: {len(classes)}")

        if classes:
            lines.append(f"- Classes: {', '.join(classes)}")

        if class_counts_by_name:
            lines.append("")
            lines.append("Per-class object counts:")
            for cls_name, count in class_counts_by_name.items():
                lines.append(f"  - {cls_name}: {count}")

        lines.append("")

    # ----------------------------------------------------------------------
    # Metrics section
    # ----------------------------------------------------------------------
    if metrics_info is not None:
        per_class = metrics_info.get("per_class", {})
        summary_all = metrics_info.get("summary_all")
        metric_classes = metrics_info.get("classes", [])

        lines.append("Model performance metrics (from Excel):")
        lines.append("")

        # Overall metrics ("all" row)
        if summary_all is not None:
            prec = summary_all.get("Precision", "Not specified")
            rec = summary_all.get("Recall", "Not specified")
            f1 = summary_all.get("F1", "Not specified")
            ap = summary_all.get("AP@0.5", "Not specified")
            gt = summary_all.get("GT", "Not specified")
            tp = summary_all.get("TP", "Not specified")
            fp = summary_all.get("FP", "Not specified")
            fn = summary_all.get("FN", "Not specified")
            wrong_cls = summary_all.get("Wrong Class", "Not specified")

            lines.append("Overall (row 'all'):")
            lines.append(
                f"- Precision: {prec}, Recall: {rec}, F1: {f1}, AP@0.5: {ap}"
            )
            lines.append(
                f"- GT: {gt}, TP: {tp}, FP: {fp}, FN: {fn}, Wrong Class: {wrong_cls}"
            )
            lines.append("")

        # Per-class metrics
        if per_class and metric_classes:
            lines.append("Per-class metrics:")
            for cls_name in metric_classes:
                row = per_class.get(cls_name, {})
                prec = row.get("Precision", "Not specified")
                rec = row.get("Recall", "Not specified")
                f1 = row.get("F1", "Not specified")
                ap = row.get("AP@0.5", "Not specified")
                gt = row.get("GT", "Not specified")
                tp = row.get("TP", "Not specified")
                fp = row.get("FP", "Not specified")
                fn = row.get("FN", "Not specified")
                wrong_cls = row.get("Wrong Class", "Not specified")

                lines.append(f"- Class: {cls_name}")
                lines.append(
                    f"  - Precision: {prec}, Recall: {rec}, F1: {f1}, AP@0.5: {ap}"
                )
                lines.append(
                    f"  - GT: {gt}, TP: {tp}, FP: {fp}, FN: {fn}, Wrong Class: {wrong_cls}"
                )
            lines.append("")

    # ----------------------------------------------------------------------
    # ONNX model technical summary
    # ----------------------------------------------------------------------
    if onnx_info is not None:
        num_parameters = onnx_info.get("num_parameters", "Not specified")
        inputs = onnx_info.get("inputs", [])
        outputs = onnx_info.get("outputs", [])

        lines.append("Model technical summary (from ONNX):")
        lines.append("")
        lines.append(f"- Approximate number of parameters: {num_parameters}")

        if inputs:
            lines.append("")
            lines.append("Model inputs:")
            for inp in inputs:
                name = inp.get("name", "unnamed_input")
                dtype = inp.get("dtype", "unknown")
                shape = inp.get("shape", [])
                shape_str = ", ".join(str(s) for s in shape) if shape else "unknown"
                lines.append(f"  - {name}: dtype = {dtype}, shape = [{shape_str}]")

        if outputs:
            lines.append("")
            lines.append("Model outputs:")
            for out in outputs:
                name = out.get("name", "unnamed_output")
                dtype = out.get("dtype", "unknown")
                shape = out.get("shape", [])
                shape_str = ", ".join(str(s) for s in shape) if shape else "unknown"
                lines.append(f"  - {name}: dtype = {dtype}, shape = [{shape_str}]")

        lines.append("")

    # ----------------------------------------------------------------------
    # Instructions to the LLM
    # ----------------------------------------------------------------------
    lines.append(
        "Use all the information above to write the documentation. "
        "If certain details are not explicitly provided, state that they are "
        "not specified instead of guessing."
    )
    lines.append(
        "The first heading should be the project name as an H1 (#). "
        "Then follow a clear, professional structure that makes sense for the "
        "given project type, using the 'Recommended sections' list as guidance "
        "when available. Include a dedicated section summarising the model's "
        "inputs, outputs and parameter count based on the ONNX information."
    )

    return "\n".join(lines)
