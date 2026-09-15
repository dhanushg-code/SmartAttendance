"""Periodic schedule alerts and multi-channel notifiers (desktop tray + sound + SMTP email)."""
from __future__ import annotations

import logging
import os
import smtplib
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from config import settings
from database import timetable as timetable_service

logger = logging.getLogger(__name__)

# State tracking: set of (date_str, timetable_id) to guarantee 1 alert per period per day
_alerted_today: set[tuple[str, str]] = set()


def reset_alert_state() -> None:
    """Clear the alert cache (used for unit/smoke tests)."""
    global _alerted_today
    _alerted_today.clear()


def get_alert_state() -> set[tuple[str, str]]:
    """Inspect current alerted keys."""
    return set(_alerted_today)


# ---------------------------------------------------------------------------
# Notifier Interface & Implementations
# ---------------------------------------------------------------------------

class Notifier(ABC):
    """Abstract notification channel."""

    @abstractmethod
    def notify(self, alert_payload: dict[str, Any]) -> bool:
        """Deliver an alert for an upcoming timetable period."""
        pass


class DesktopNotifier(Notifier):
    """Fires a Windows system tray toast and plays an audio cue."""

    def __init__(self, tray_icon: Any = None, sound_file: Optional[str] = None) -> None:
        self.tray_icon = tray_icon
        self.sound_file = sound_file

    def notify(self, alert_payload: dict[str, Any]) -> bool:
        subject = alert_payload.get("subject_name") or alert_payload.get("subject_code") or "Class"
        sclass = alert_payload.get("class", "Class")
        period_no = alert_payload.get("period_no", "?")
        start_time = alert_payload.get("start_time", "")
        room = alert_payload.get("room") or "TBA"
        staff = alert_payload.get("staff_name") or "Staff"

        title = f"🔔 Upcoming Class: {sclass} ({subject})"
        message = (
            f"Period {period_no} begins at {start_time} in Room {room}.\n"
            f"Instructor: {staff}"
        )

        # 1. System Tray Toast Notification
        if self.tray_icon is not None:
            try:
                from PySide6.QtWidgets import QSystemTrayIcon
                self.tray_icon.showMessage(
                    title,
                    message,
                    QSystemTrayIcon.MessageIcon.Information,
                    7000,
                )
            except Exception as exc:
                logger.warning("Tray notification failed: %s", exc)

        # 2. Sound via playsound (with fallback to system beep)
        self._play_alert_sound()
        return True

    def _play_alert_sound(self) -> None:
        try:
            from playsound import playsound
            if self.sound_file and os.path.exists(self.sound_file):
                playsound(self.sound_file, block=False)
            else:
                self._fallback_beep()
        except Exception as exc:
            logger.warning("Sound playback failed (%s), using fallback beep", exc)
            self._fallback_beep()

    @staticmethod
    def _fallback_beep() -> None:
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


class EmailNotifier(Notifier):
    """Sends email alerts to staff members via SMTP using settings from .env."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        sender: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ) -> None:
        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.user = user if user is not None else settings.SMTP_USER
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.sender = sender if sender is not None else settings.SMTP_FROM
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.sent_emails: list[dict[str, Any]] = []

    def notify(self, alert_payload: dict[str, Any]) -> bool:
        recipient = alert_payload.get("staff_email", "").strip()
        if not recipient:
            logger.debug("No staff email configured for period %s", alert_payload.get("id"))
            return False

        subject_title = alert_payload.get("subject_name") or alert_payload.get("subject_code") or "Class"
        sclass = alert_payload.get("class", "Class")
        period_no = alert_payload.get("period_no", "?")
        start_time = alert_payload.get("start_time", "")
        room = alert_payload.get("room") or "TBA"
        staff_name = alert_payload.get("staff_name") or "Faculty Member"

        subject = f"[SmartAttend Alert] Period {period_no} ({sclass} - {subject_title}) starts at {start_time}"
        body = (
            f"Dear {staff_name},\n\n"
            f"This is an automated reminder from SmartAttend.\n\n"
            f"Your upcoming class is scheduled to begin in less than 10 minutes:\n"
            f"  • Class/Section: {sclass}\n"
            f"  • Subject:       {subject_title}\n"
            f"  • Period:        {period_no}\n"
            f"  • Start Time:    {start_time}\n"
            f"  • Room / Hall:   {room}\n\n"
            f"Please ensure attendance kiosk terminal is initialized.\n\n"
            f"Best regards,\n"
            f"SmartAttend Notification System"
        )

        email_record = {
            "to": recipient,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat(),
        }
        self.sent_emails.append(email_record)

        # If running in DEMO_MODE or without SMTP credentials, record and mock succeed
        if settings.DEMO_MODE or not self.user:
            logger.info("Demo mode: simulated email alert successfully delivered to %s", recipient)
            return True

        # Live SMTP delivery
        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)
            logger.info("Email alert successfully dispatched to %s", recipient)
            return True
        except Exception as exc:
            logger.error("Failed to send email alert to %s: %s", recipient, exc)
            return False


class CompositeNotifier(Notifier):
    """Fan-out notifier calling multiple notifiers."""

    def __init__(self, notifiers: list[Notifier]) -> None:
        self.notifiers = list(notifiers)

    def notify(self, alert_payload: dict[str, Any]) -> bool:
        any_success = False
        for n in self.notifiers:
            try:
                if n.notify(alert_payload):
                    any_success = True
            except Exception as exc:
                logger.error("Notifier error in %s: %s", type(n).__name__, exc)
        return any_success


# ---------------------------------------------------------------------------
# Core Period Alert Checker
# ---------------------------------------------------------------------------

def _parse_time_str(time_val: Any) -> time:
    """Parse string HH:MM[:SS] into datetime.time."""
    if isinstance(time_val, time):
        return time_val
    s = str(time_val).strip()
    parts = s.split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    sec = int(parts[2].split(".")[0]) if len(parts) > 2 else 0
    return time(h, m, sec)


def check_upcoming_periods(
    now: Optional[datetime] = None,
    notifiers: Optional[list[Notifier] | Notifier] = None,
) -> list[dict[str, Any]]:
    """Check for periods starting within the next 10 minutes that haven't been alerted today.

    Calls the provided Notifier(s) and returns a list of newly alerted periods.
    Guarantees exactly one alert fires per period per day.
    """
    global _alerted_today
    if now is None:
        now = datetime.now()

    today_str = now.date().isoformat()
    day_name = now.strftime("%A")  # e.g. "Monday"

    # Query today's periods from timetable
    candidates = timetable_service.list_timetable(day_of_week=day_name)
    alerted_periods: list[dict[str, Any]] = []

    # Normalize notifiers
    notifier_list: list[Notifier] = []
    if isinstance(notifiers, list):
        notifier_list = notifiers
    elif isinstance(notifiers, Notifier):
        notifier_list = [notifiers]

    for raw_slot in candidates:
        slot = timetable_service.enrich_slot(raw_slot)
        slot_id = slot.get("id") or f"{slot.get('class')}_{slot.get('day_of_week')}_{slot.get('period_no')}"
        cache_key = (today_str, slot_id)

        # Skip if already alerted today
        if cache_key in _alerted_today:
            continue

        raw_start = slot.get("start_time")
        if not raw_start:
            continue

        start_t = _parse_time_str(raw_start)
        period_start_dt = datetime.combine(now.date(), start_t)

        # Difference in seconds between period start and now
        delta_seconds = (period_start_dt - now).total_seconds()

        # Alert if starting in the next 10 minutes (0 <= delta <= 600 seconds)
        if 0 <= delta_seconds <= 600:
            _alerted_today.add(cache_key)
            alerted_periods.append(slot)

            # Call notifiers
            for notifier in notifier_list:
                try:
                    notifier.notify(slot)
                except Exception as exc:
                    logger.error("Notification dispatch failed: %s", exc)

    return alerted_periods
