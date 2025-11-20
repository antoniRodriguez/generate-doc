# src/docgen/hardware.py
#
# GPU detection, model size inference and hardware-aware hints.

import re
import subprocess
from dataclasses import dataclass
from typing import Optional

from .logging_utils import log_info, log_warning, log_gpu, log_model


@dataclass
class GPUInfo:
    name: str
    vram_gb: float
    tier: str  # "cpu", "low", "mid", "high"


def _detect_gpu_with_nvidia_smi() -> Optional[GPUInfo]:
    """
    Try to detect GPU info using nvidia-smi.
    Returns GPUInfo or None if detection fails.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout.strip()
        if not output:
            return None

        first_line = output.splitlines()[0]
        parts = [p.strip() for p in first_line.split(",")]
        if len(parts) < 2:
            return None

        name = parts[0]
        try:
            mem_mib = float(parts[1])
        except ValueError:
            mem_mib = 0.0

        vram_gb = mem_mib / 1024.0 if mem_mib > 0 else 0.0

        if vram_gb <= 0:
            tier = "cpu"
        elif vram_gb < 4:
            tier = "low"
        elif vram_gb < 10:
            tier = "mid"
        else:
            tier = "high"

        return GPUInfo(name=name, vram_gb=vram_gb, tier=tier)

    except Exception:
        return None


def _detect_gpu_with_torch() -> Optional[GPUInfo]:
    """
    Fallback GPU detection using PyTorch if available.
    Returns GPUInfo or None if detection fails or torch is not present.
    """
    try:
        import torch  # type: ignore

        if not torch.cuda.is_available():
            return None

        device_index = 0
        name = torch.cuda.get_device_name(device_index)
        props = torch.cuda.get_device_properties(device_index)
        vram_gb = float(props.total_memory) / (1024.0 ** 3)

        if vram_gb < 4:
            tier = "low"
        elif vram_gb < 10:
            tier = "mid"
        else:
            tier = "high"

        return GPUInfo(name=name, vram_gb=vram_gb, tier=tier)

    except Exception:
        return None


def detect_gpu() -> GPUInfo:
    """
    Detect GPU info using nvidia-smi or PyTorch.
    If everything fails, assume CPU.
    """
    gpu = _detect_gpu_with_nvidia_smi()
    if gpu is not None:
        return gpu

    gpu = _detect_gpu_with_torch()
    if gpu is not None:
        return gpu

    return GPUInfo(name="CPU", vram_gb=0.0, tier="cpu")


def infer_model_size_label(model_name: str) -> str:
    """
    Infer a rough size label ("small", "medium", "large", "unknown")
    based on the model name (e.g. deepseek-r1:1.5b, deepseek-r1:8b).
    """
    # Look for fragments like "1.5b" or "8b"
    match = re.search(r"(\d+(\.\d+)?)\s*b", model_name.lower())
    if not match:
        return "unknown"

    try:
        size_b = float(match.group(1))
    except ValueError:
        return "unknown"

    if size_b < 4:
        return "small"
    elif size_b < 10:
        return "medium"
    else:
        return "large"


def print_gpu_and_model_hint(gpu: GPUInfo, model_name: str, size_label: str) -> None:
    """
    Print a hardware-aware, slightly humorous hint before calling the LLM.
    """
    if gpu.tier == "cpu":
        log_warning(
            "No compatible GPU detected. Running on CPU only. "
            "This may take a while, so feel free to grab a coffee or tidy up your dataset folders."
        )
        return

    log_gpu(f"{gpu.name} detected (~{gpu.vram_gb:.1f} GB VRAM, tier: {gpu.tier}).")
    log_model(f"Using model: {model_name} (size: {size_label}).")

    if gpu.tier == "low":
        if size_label in ("small", "medium"):
            log_info(
                "Modest model on a modest GPU. It should work, but the first load "
                "might be a bit dramatic."
            )
        else:
            log_warning(
                "Large model on a low-VRAM GPU detected. "
                "You might want to grab a coffee. Maybe two."
            )

    elif gpu.tier == "mid":
        if size_label in ("small", "medium"):
            log_info(
                "Nice mid-tier setup. The first generation may take a moment while "
                "the model warms up, but it should be reasonably snappy afterwards."
            )
        else:
            log_info(
                "Mid-tier GPU with a large model. It will work, but do not be surprised "
                "if you have time to skim your emails before the doc appears."
            )

    elif gpu.tier == "high":
        log_info(
            "High-tier GPU detected. This should be relatively quick. "
            "If it is not, we will blame the model, not your hardware."
        )
