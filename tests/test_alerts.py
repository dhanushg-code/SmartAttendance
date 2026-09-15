"""Smoke tests for timetable period alerts and notifiers with faked clock."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings
assert settings.DEMO_MODE, "test_alerts requires DEMO_MODE=true"

from database import staff as staff_service
from database import students as student_service
from database import timetable as timetable_service
from timetable.alerts import (
    DesktopNotifier,
    EmailNotifier,
    Notifier,
    check_upcoming_periods,
    reset_alert_state,
)


class MockNotifier(Notifier):
    def __init__(self) -> None:
        self.alerts: list[dict[str, Any]] = []

    def notify(self, alert_payload: dict[str, Any]) -> bool:
        self.alerts.append(alert_payload)
        return True


def run_tests() -> None:
    reset_alert_state()

    # 1. Setup sample subject, staff, and timetable slot
    if not student_service.subjects():
        student_service.add_subject("CS101", "Intro to Programming")
    subj = student_service.subjects()[0]

    stf = staff_service.get_staff_by_email("test.prof@university.edu")
    if not stf:
        stf = staff_service.add_staff(
            name="Prof. Test",
            email="test.prof@university.edu",
            phone="+1 555-9999",
            device_token="dev_tok_test",
        )

    # Monday Period 1: 09:00 - 10:00
    timetable_service.save_slot(
        class_name="TEST-CLASS",
        day_of_week="Monday",
        period_no=1,
        start_time="09:00",
        end_time="10:00",
        subject_id=subj["id"],
        staff_id=stf["id"],
        room="Hall 404",
    )

    # Monday Period 2: 11:00 - 12:00 (far away)
    timetable_service.save_slot(
        class_name="TEST-CLASS",
        day_of_week="Monday",
        period_no=2,
        start_time="11:00",
        end_time="12:00",
        subject_id=subj["id"],
        staff_id=stf["id"],
        room="Hall 405",
    )

    mock = MockNotifier()
    email_notifier = EmailNotifier()
    desktop_notifier = DesktopNotifier()

    # -------------------------------------------------------------
    # Test 1: Clock faked to 08:45 (15 min before Period 1) -> No alert
    # -------------------------------------------------------------
    # 2026-09-14 is a Monday
    t_early = datetime(2026, 9, 14, 8, 45, 0)
    alerts = check_upcoming_periods(now=t_early, notifiers=[mock, email_notifier])
    test_alerts = [a for a in alerts if a["class"] == "TEST-CLASS"]
    assert len(test_alerts) == 0, f"Expected 0 alerts for TEST-CLASS at 08:45, got {len(test_alerts)}"

    # -------------------------------------------------------------
    # Test 2: Clock faked to 08:52 (8 min before Period 1) -> Alert fires!
    # -------------------------------------------------------------
    t_upcoming = datetime(2026, 9, 14, 8, 52, 0)
    alerts = check_upcoming_periods(now=t_upcoming, notifiers=[mock, email_notifier, desktop_notifier])
    test_alerts = [a for a in alerts if a["class"] == "TEST-CLASS"]
    assert len(test_alerts) == 1, f"Expected 1 alert for TEST-CLASS at 08:52, got {len(test_alerts)}"

    mock_test = [a for a in mock.alerts if a["class"] == "TEST-CLASS"]
    assert len(mock_test) == 1, f"MockNotifier should receive 1 alert for TEST-CLASS, got {len(mock_test)}"

    emails_test = [e for e in email_notifier.sent_emails if e["to"] == "test.prof@university.edu"]
    assert len(emails_test) == 1, f"EmailNotifier should send 1 email to test.prof, got {len(emails_test)}"

    sent = emails_test[0]
    assert "Period 1" in sent["subject"]
    assert "TEST-CLASS" in sent["subject"]
    assert "Hall 404" in sent["body"]

    # -------------------------------------------------------------
    # Test 3: Clock faked to 08:56 (4 min before Period 1, same day) -> DUPLICATE SUPPRESSED
    # -------------------------------------------------------------
    t_dup = datetime(2026, 9, 14, 8, 56, 0)
    alerts_dup = check_upcoming_periods(now=t_dup, notifiers=[mock, email_notifier])
    test_dup = [a for a in alerts_dup if a["class"] == "TEST-CLASS"]
    assert len(test_dup) == 0, f"Duplicate check failed: expected 0 alerts for TEST-CLASS, got {len(test_dup)}"

    mock_test_dup = [a for a in mock.alerts if a["class"] == "TEST-CLASS"]
    assert len(mock_test_dup) == 1, "MockNotifier count for TEST-CLASS must remain 1 on same day"

    emails_test_dup = [e for e in email_notifier.sent_emails if e["to"] == "test.prof@university.edu"]
    assert len(emails_test_dup) == 1, "EmailNotifier count for test.prof must remain 1 on same day"

    # -------------------------------------------------------------
    # Test 4: Next Monday (2026-09-21 08:53) -> Fires again for the new day
    # -------------------------------------------------------------
    t_next_week = datetime(2026, 9, 21, 8, 53, 0)
    alerts_next = check_upcoming_periods(now=t_next_week, notifiers=[mock, email_notifier])
    test_next = [a for a in alerts_next if a["class"] == "TEST-CLASS"]
    assert len(test_next) == 1, f"Expected 1 alert for TEST-CLASS on next week Monday, got {len(test_next)}"

    mock_test_next = [a for a in mock.alerts if a["class"] == "TEST-CLASS"]
    assert len(mock_test_next) == 2, f"MockNotifier should have 2 total alerts for TEST-CLASS, got {len(mock_test_next)}"

    emails_test_next = [e for e in email_notifier.sent_emails if e["to"] == "test.prof@university.edu"]
    assert len(emails_test_next) == 2, f"EmailNotifier should have 2 total emails for test.prof, got {len(emails_test_next)}"

    # -------------------------------------------------------------
    # Test 5: Different day of week (Tuesday 08:53) -> Monday periods don't fire
    # -------------------------------------------------------------
    t_tuesday = datetime(2026, 9, 15, 8, 53, 0)
    alerts_tue = check_upcoming_periods(now=t_tuesday, notifiers=[mock])
    # Only if Tuesday had periods would it fire; TEST-CLASS has none on Tuesday
    assert not any(a["class"] == "TEST-CLASS" for a in alerts_tue)

    print("ALL PERIOD ALERT & NOTIFIER TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_tests()
