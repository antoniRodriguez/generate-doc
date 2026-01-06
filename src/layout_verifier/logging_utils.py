# src/layout_verifier/logging_utils.py
#
# Colored logging helpers for the layout verifier.

RESET = "\033[0m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"


def log_info(msg: str) -> None:
    print(f"{GREEN}[INFO]{RESET} {msg}")


def log_warning(msg: str) -> None:
    print(f"{YELLOW}[WARNING]{RESET} {msg}")


def log_error(msg: str) -> None:
    print(f"{RED}[ERROR]{RESET} {msg}")


def log_gpu(msg: str) -> None:
    print(f"{CYAN}[GPU]{RESET} {msg}")


def log_model(msg: str) -> None:
    print(f"{MAGENTA}[MODEL]{RESET} {msg}")


def log_llm(msg: str) -> None:
    print(f"{CYAN}[LLM]{RESET} {msg}")
