"""Classroom attendance screen with live biometric scanning HUD and feed."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from attendance.attendance import AttendanceService
from database import students as student_service
from fingerprint.scanner import ScanEvent, ScannerService
from ui.common import BiometricScanHUD, ScanBridge, StatusPill, set_pill


class AttendanceWidget(QWidget):
    def __init__(self, parent=None, scanner_service: ScannerService | None = None) -> None:
        super().__init__(parent)
        self.scanner_service = scanner_service or ScannerService()
        self.attendance = AttendanceService()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        # -------------------------------------------------------------
        # 1. Subject Selector & Action Toolbar
        # -------------------------------------------------------------
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        lbl_subj = QLabel("COURSE / SUBJECT:")
        lbl_subj.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        toolbar.addWidget(lbl_subj)

        self.subject_combo = QComboBox()
        self.subject_combo.setFixedHeight(40)
        self._load_subjects()
        self.subject_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.subject_combo, 2)

        self.start_btn = QPushButton("▶  Start Live Scanner")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self._start_scan)
        toolbar.addWidget(self.start_btn)

        export_btn = QPushButton("📑 Export Daily Excel")
        export_btn.setObjectName("successBtn")
        export_btn.setFixedHeight(40)
        export_btn.clicked.connect(self._export)
        toolbar.addWidget(export_btn)

        refresh_btn = QPushButton("🔄 Refresh Feed")
        refresh_btn.setFixedHeight(40)
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        root.addLayout(toolbar)

        # -------------------------------------------------------------
        # 2. Futuristic Biometric Scanner HUD
        # -------------------------------------------------------------
        self.scanner_hud = BiometricScanHUD("CLASSROOM BIOMETRIC SCANNER", self)
        root.addWidget(self.scanner_hud)

        # Retain status_label reference for backwards compatibility
        self.status_label = self.scanner_hud.main_text

        # -------------------------------------------------------------
        # 3. Live Attendance Feed Table
        # -------------------------------------------------------------
        feed_header = QHBoxLayout()
        feed_title = QLabel("LIVE ATTENDANCE VERIFICATION LOG")
        feed_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        feed_header.addWidget(feed_title)
        feed_header.addStretch(1)

        self.count_pill = StatusPill("0 Verified", "success")
        feed_header.addWidget(self.count_pill)
        root.addLayout(feed_header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Scan Time", "Register No", "Student Name", "Class", "Status"])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.table, 1)

        # Scanner events arrive on a worker thread; ScanBridge re-emits on the
        # Qt main thread so we can touch widgets safely.
        self.scan_bridge = ScanBridge(self.scanner_service, self)
        self.scan_bridge.scanned.connect(self._on_scan)

    def _load_subjects(self) -> None:
        self.subject_combo.clear()
        for sub in student_service.subjects():
            self.subject_combo.addItem(f"{sub['code']} — {sub['name']}", sub["id"])
        if self.subject_combo.count() == 0:
            self.subject_combo.addItem("No subjects configured", "")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        subject_id = self.subject_combo.currentData()
        rows = self.attendance.today_rows(subject_id or None)
        students = {s["id"]: s for s in student_service.list_students()}
        subjects = {s["id"]: s for s in student_service.subjects()}

        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            stu = students.get(row["student_id"], {})
            sub = subjects.get(row.get("subject_id"), {})
            entry_time = str(row.get("entry_time") or "")[:5]
            if not entry_time:
                entry_time = datetime.now().strftime("%H:%M")

            status_str = f"✔ {row.get('status')} ({sub.get('code', '')})"

            self.table.setItem(r, 0, QTableWidgetItem(entry_time))
            self.table.setItem(r, 1, QTableWidgetItem(stu.get("register_no", "—")))
            self.table.setItem(r, 2, QTableWidgetItem(stu.get("name", "—")))
            self.table.setItem(r, 3, QTableWidgetItem(stu.get("class", "—")))
            self.table.setItem(r, 4, QTableWidgetItem(status_str))

        set_pill(self.count_pill, f"● {len(rows)} Students Logged Today", "success")

    def _start_scan(self) -> None:
        if not self.subject_combo.currentData():
            QMessageBox.warning(
                self, "Subject Required", "Please select a subject or configure subjects first."
            )
            return
        self.scanner_hud.set_scanning()
        self.start_btn.setText("⚡ Scanner Active (Listening…)")
        self.start_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #312E81;
                border: 1px solid #818CF8;
                color: #C7D2FE;
                font-weight: 700;
            }
            """
        )
        self.scanner_service.start()

    def _on_scan(self, event: ScanEvent) -> None:
        from fingerprint.verification import VerificationService

        result = VerificationService(self.scanner_service).identify_event(event)
        if not result.success:
            self.scanner_hud.set_error(
                "Biometric Verification Failed",
                f"Unknown fingerprint pattern — {result.message}",
            )
            return

        student = result.student
        subject_id = self.subject_combo.currentData()
        mark = self.attendance.mark_present(student, subject_id)

        now_str = datetime.now().strftime("%I:%M:%S %p")
        if mark.duplicate:
            self.scanner_hud.set_duplicate(
                f"Already Logged: {student['name']} ({student['register_no']})",
                f"Duplicate scan detected. Attendance was previously marked for today.",
            )
        else:
            self.scanner_hud.set_success(
                f"Verified: {student['name']} ({student['register_no']})",
                f"Marked PRESENT for {student.get('class', '')} at {now_str} • Record stored in database",
            )

        self.refresh()

    def _export(self) -> None:
        from excel.excel_export import export_daily

        path = export_daily()
        QMessageBox.information(
            self,
            "Daily Report Exported",
            f"Classroom attendance exported successfully:\n\n{path}",
        )
