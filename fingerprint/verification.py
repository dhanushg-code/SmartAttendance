"""Fingerprint verification/identification: template id → student row.

Works in both modes:
- demo: the SimulatedScanner returns the typed id; we look it up in Supabase.
- live: SDKScanner.identify() performs a 1:N match, then the template id is
  translated to the student through the students table.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from database.supabase_client import db
from fingerprint.scanner import ScannerService


@dataclass
class IdentityResult:
    success: bool
    student: Optional[dict] = None
    message: str = ""


class VerificationService:
    def __init__(self, scanner_service: Optional[ScannerService] = None) -> None:
        self.scanner_service = scanner_service or ScannerService()

    def scan_and_identify(self) -> IdentityResult:
        event = self.scanner_service.capture_once()
        return self.identify_event(event)

    def identify_event(self, event) -> IdentityResult:
        if not event.success or not event.template_id:
            return IdentityResult(False, message=event.message or "Scan failed")
        return self.identify_template(event.template_id)

    def identify_template(self, template_id: str) -> IdentityResult:
        rows = (
            db.table("students")
            .select("*")
            .eq("fingerprint_id", template_id)
            .execute()
            .data
        )
        if not rows:
            return IdentityResult(False, message="Fingerprint not recognised")
        return IdentityResult(True, student=rows[0], message="Identified")
