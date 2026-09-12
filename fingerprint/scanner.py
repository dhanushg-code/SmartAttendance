"""Fingerprint scanner abstraction.

The application only talks to the `FingerprintScanner` interface. The concrete
backend is chosen at runtime:

- ``SimulatedScanner``  — keyboard-driven demo mode (no hardware needed).
- ``SDKScanner``        — adapter around your scanner vendor's SDK/API.

Since every USB scanner ships a different SDK (Mantra, SecuGen, ZKTeco, ...),
only this file must change when the exact model is chosen. Typical SDK flow
implemented by ``SDKScanner``:

1. ``open()``  → initialise device handle (SDK DLL / RD service / COM API).
2. ``capture()`` → grab a live template or image → convert to template.
3. ``identify(template)`` → 1:N match against enrolled templates.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Optional


class ScanEvent:
    """A single fingerprint read result."""

    def __init__(self, template_id: Optional[str], success: bool, message: str = "") -> None:
        self.template_id = template_id
        self.success = success
        self.message = message

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"ScanEvent(id={self.template_id!r}, ok={self.success}, msg={self.message!r})"


class FingerprintScanner:
    """Interface every scanner backend implements."""

    def open(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def is_open(self) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def capture(self) -> ScanEvent:  # pragma: no cover - interface
        raise NotImplementedError

    def identify(self, template_id: str) -> Optional[str]:  # pragma: no cover - interface
        """1:N match; returns matched template id or None."""
        raise NotImplementedError


class SimulatedScanner(FingerprintScanner):
    """Demo backend: the operator 'scans' by typing the fingerprint id.

    This keeps every downstream flow (enrollment, attendance, exams) fully
    testable without hardware.
    """

    def __init__(self) -> None:
        self._open = False
        self._enrolled: dict[str, str] = {}  # template_id -> "template" blob

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def capture(self) -> ScanEvent:
        if not self._open:
            return ScanEvent(None, False, "Scanner not open")
        try:
            raw = input("Simulated scan — enter fingerprint id (or blank to cancel): ").strip()
        except (EOFError, KeyboardInterrupt):
            return ScanEvent(None, False, "Scan cancelled")
        if not raw:
            return ScanEvent(None, False, "Scan cancelled")
        return ScanEvent(raw, True)

    def identify(self, template_id: str) -> Optional[str]:
        if template_id in self._enrolled:
            return template_id
        return None

    # --- helpers used by demo enrollment -------------------------------------
    def enroll(self, template_id: str) -> bool:
        self._enrolled.setdefault(template_id, f"sim-template:{template_id}")
        return True


class SDKScanner(FingerprintScanner):
    """Adapter for a real vendor SDK. Wire the vendor calls into the four
    marked hooks below; no other file changes."""

    def __init__(self, sdk_config: Optional[dict] = None) -> None:
        self._sdk_config = sdk_config or {}
        self._open = False
        self._sdk = None  # vendor SDK handle/module goes here

    def open(self) -> None:  # pragma: no cover - needs hardware
        # HOOK 1: load the vendor SDK / open the device, e.g.
        #   self._sdk = vendor_sdk.Device(**self._sdk_config)
        #   self._sdk.init()
        self._open = True

    def close(self) -> None:  # pragma: no cover - needs hardware
        # HOOK 2: release the device, e.g. self._sdk.close()
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def capture(self) -> ScanEvent:  # pragma: no cover - needs hardware
        # HOOK 3: capture image → extract template via vendor API. Return
        # ScanEvent(template_bytes_or_id, True) on success.
        raise NotImplementedError("Wire the vendor SDK capture here")

    def identify(self, template_id: str) -> Optional[str]:  # pragma: no cover
        # HOOK 4: 1:N match of the fresh capture against enrolled templates.
        # Most SDKs expose MatchScore / Identify functions — call them here.
        raise NotImplementedError("Wire the vendor SDK matching here")


def make_scanner() -> FingerprintScanner:
    """Factory used by the app; respects demo mode."""
    from config import settings

    if settings.DEMO_MODE:
        return SimulatedScanner()
    return SDKScanner()


class ScannerService:
    """Background scan listener bridging scanner events into Qt/UI callbacks.

    UI code subscribes with ``on_scan(callback)`` and gets called on a worker
    thread with a ``ScanEvent`` — the callback must marshal to the GUI thread.
    """

    def __init__(self, scanner: Optional[FingerprintScanner] = None) -> None:
        self.scanner = scanner or make_scanner()
        self._callbacks: list[Callable[[ScanEvent], None]] = []
        self._queue: "queue.Queue[ScanEvent]" = queue.Queue()
        self._worker: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def open(self) -> None:
        if not self.scanner.is_open():
            self.scanner.open()

    def close(self) -> None:
        self.stop()
        if self.scanner.is_open():
            self.scanner.close()

    def on_scan(self, callback: Callable[[ScanEvent], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
        self.open()
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def _loop(self) -> None:  # pragma: no cover - threading loop
        while self._running:
            try:
                event = self.scanner.capture()
            except Exception as exc:  # keep the loop alive on SDK hiccups
                event = ScanEvent(None, False, f"Scanner error: {exc}")
                time.sleep(0.5)
            self._queue.put(event)
            self._dispatch(event)

    def _dispatch(self, event: ScanEvent) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                pass  # never let one bad listener kill the loop

    def capture_once(self) -> ScanEvent:
        """Synchronous single capture (used by enrollment dialog)."""
        self.open()
        return self.scanner.capture()
