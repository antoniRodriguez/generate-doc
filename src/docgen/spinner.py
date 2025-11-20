# src/docgen/spinner.py
#
# Simple CLI spinner using a background thread.
# Used to show activity during the LLM call.

import threading
import time
from typing import Optional

from .logging_utils import CYAN, RESET


class Spinner:
    def __init__(self, message: str = "Working...") -> None:
        self.message = message
        self.spinner_cycle = ["-", "\\", "|", "/"]
        self.running = False
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def _spin(self) -> None:
        idx = 0
        while self.running:
            symbol = self.spinner_cycle[idx]
            print(
                f"\r{CYAN}[LLM]{RESET} {self.message} {symbol}",
                end="",
                flush=True,
            )
            idx = (idx + 1) % len(self.spinner_cycle)
            time.sleep(0.1)

    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        time.sleep(0.15)
        print("\r", end="", flush=True)
