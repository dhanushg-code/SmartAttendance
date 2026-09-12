"""Exam management + futuristic biometric exam kiosk terminal (spec sections 10-15, 25)."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import students as student_service
from exams import exams as exam_service
from fingerprint.scanner import ScanEvent, ScannerService
from ui.common import BiometricScanHUD, ScanBridge, StatusPill, set_pill


class ExamsWidget(QWidget):
    """Exam setup: create exam, add eligible students, halls, seats, allocate."""

    def __init__(self, parent=None, scanner_service: ScannerService | None = None) -> None:
        super().__init__(parent)
        self.scanner_service = scanner_service or ScannerService()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # -------------------------------------------------------------
        # 1. Exam Selector & Actions Bar
        # -------------------------------------------------------------
        top = QHBoxLayout()
        top.setSpacing(10)

        lbl_exam = QLabel("ACTIVE EXAM:")
        lbl_exam.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        top.addWidget(lbl_exam)

        self.exam_combo = QComboBox()
        self.exam_combo.setFixedHeight(40)
        self.exam_combo.currentIndexChanged.connect(self._refresh_details)
        top.addWidget(self.exam_combo, 2)

        new_btn = QPushButton("➕ New Exam…")
        new_btn.setObjectName("primaryBtn")
        new_btn.setFixedHeight(40)
        new_btn.clicked.connect(self._new_exam)
        top.addWidget(new_btn)

        elig_btn = QPushButton("👥 Add Eligible Students…")
        elig_btn.setFixedHeight(40)
        elig_btn.clicked.connect(self._add_eligible)
        top.addWidget(elig_btn)

        root.addLayout(top)

        # -------------------------------------------------------------
        # 2. Exam Summary Hero Card
        # -------------------------------------------------------------
        hero_card = QFrame()
        hero_card.setObjectName("examHero")
        hero_card.setStyleSheet(
            """
            QFrame#examHero {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #15223D, stop:1 #111A2E);
                border: 1px solid #22355A;
                border-radius: 12px;
            }
            """
        )
        h_lay = QVBoxLayout(hero_card)
        h_lay.setContentsMargins(18, 16, 18, 16)
        h_lay.setSpacing(10)

        top_info = QHBoxLayout()
        self.info_title = QLabel("No Exam Selected")
        self.info_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #F8FAFC;")
        top_info.addWidget(self.info_title, 1)

        self.pill_eligible = StatusPill("0 Eligible", "info")
        self.pill_allocated = StatusPill("0 Allocated", "purple")
        self.pill_verified = StatusPill("0 Verified", "success")
        top_info.addWidget(self.pill_eligible)
        top_info.addWidget(self.pill_allocated)
        top_info.addWidget(self.pill_verified)
        h_lay.addLayout(top_info)

        self.info_details = QLabel("Select or create an examination session to configure halls and seating.")
        self.info_details.setStyleSheet("font-size: 13px; color: #94A3B8;")
        h_lay.addWidget(self.info_details)

        root.addWidget(hero_card)

        # Compatibility info label reference
        self.info = self.info_details

        # -------------------------------------------------------------
        # 3. Halls & Seats Management Card
        # -------------------------------------------------------------
        halls_card = QFrame()
        halls_card.setObjectName("hallsCard")
        halls_card.setStyleSheet(
            """
            QFrame#hallsCard {
                background-color: #141E33;
                border: 1px solid #22314E;
                border-radius: 12px;
            }
            """
        )
        halls_lay = QVBoxLayout(halls_card)
        halls_lay.setContentsMargins(18, 18, 18, 18)
        halls_lay.setSpacing(12)

        hall_row = QHBoxLayout()
        hall_row.setSpacing(10)
        lbl_hall = QLabel("EXAM HALL:")
        lbl_hall.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        hall_row.addWidget(lbl_hall)

        self.hall_combo = QComboBox()
        self.hall_combo.setFixedHeight(36)
        self.hall_combo.currentIndexChanged.connect(self._refresh_details)
        hall_row.addWidget(self.hall_combo, 2)

        add_hall_btn = QPushButton("🏛️ New Hall…")
        add_hall_btn.setFixedHeight(36)
        add_hall_btn.clicked.connect(self._new_hall)
        hall_row.addWidget(add_hall_btn)

        gen_seats_btn = QPushButton("🪑 Generate Seats…")
        gen_seats_btn.setFixedHeight(36)
        gen_seats_btn.clicked.connect(self._generate_seats)
        hall_row.addWidget(gen_seats_btn)

        halls_lay.addLayout(hall_row)

        self.seats_table = QTableWidget()
        self.seats_table.setColumnCount(3)
        self.seats_table.setHorizontalHeaderLabels(["Seat Number", "Allocation Status", "Seat ID"])
        self.seats_table.setColumnHidden(2, True)
        self.seats_table.setAlternatingRowColors(True)
        self.seats_table.verticalHeader().setVisible(False)
        self.seats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.seats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        halls_lay.addWidget(self.seats_table)

        root.addWidget(halls_card, 1)

        # -------------------------------------------------------------
        # 4. Allocation Actions Toolbar
        # -------------------------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(12)

        alloc_btn = QPushButton("⚡ Auto-Allocate Seats")
        alloc_btn.setObjectName("primaryBtn")
        alloc_btn.setFixedHeight(40)
        alloc_btn.clicked.connect(self._allocate)
        actions.addWidget(alloc_btn)

        export_btn = QPushButton("📑 Export Exam Excel Report")
        export_btn.setObjectName("successBtn")
        export_btn.setFixedHeight(40)
        export_btn.clicked.connect(self._export_exam)
        actions.addWidget(export_btn)

        refresh_btn = QPushButton("🔄 Refresh Details")
        refresh_btn.setFixedHeight(40)
        refresh_btn.clicked.connect(self.refresh)
        actions.addWidget(refresh_btn)

        actions.addStretch(1)
        root.addLayout(actions)

        self.alloc_label = QLabel("")
        self.alloc_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        root.addWidget(self.alloc_label)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        self._load_exams()
        self._load_halls()
        self._refresh_details()

    def _load_exams(self) -> None:
        current = self.exam_combo.currentData()
        self.exam_combo.blockSignals(True)
        self.exam_combo.clear()
        for ex in exam_service.list_exams():
            self.exam_combo.addItem(
                f"{ex['exam_name']} — {ex['subject']} ({ex['exam_date']})", ex["id"]
            )
        if current:
            i = self.exam_combo.findData(current)
            if i >= 0:
                self.exam_combo.setCurrentIndex(i)
        self.exam_combo.blockSignals(False)

    def _load_halls(self) -> None:
        current = self.hall_combo.currentData()
        self.hall_combo.blockSignals(True)
        self.hall_combo.clear()
        for h in exam_service.list_halls():
            self.hall_combo.addItem(f"{h['hall_name']} (Cap: {h['capacity']})", h["id"])
        if current:
            i = self.hall_combo.findData(current)
            if i >= 0:
                self.hall_combo.setCurrentIndex(i)
        self.hall_combo.blockSignals(False)

    def _current_exam(self) -> dict | None:
        exid = self.exam_combo.currentData()
        if not exid:
            return None
        for ex in exam_service.list_exams():
            if ex["id"] == exid:
                return ex
        return None

    def _new_exam(self) -> None:
        name, ok = QInputDialog.getText(self, "New Exam Session", "Exam name:")
        if not ok or not name.strip():
            return
        subject, _ = QInputDialog.getText(self, "New Exam Session", "Subject:")
        date_s, _ = QInputDialog.getText(self, "New Exam Session", "Date (YYYY-MM-DD):")
        start, _ = QInputDialog.getText(self, "New Exam Session", "Start time (HH:MM):")
        end, _ = QInputDialog.getText(self, "New Exam Session", "End time (HH:MM):")
        try:
            exam_service.create_exam(
                name.strip(), subject.strip(), date_s.strip(), start.strip(), end.strip()
            )
        except Exception as exc:
            QMessageBox.warning(self, "Creation Failed", str(exc))
            return
        self._load_exams()

    def _add_eligible(self) -> None:
        exam = self._current_exam()
        if not exam:
            QMessageBox.information(self, "Selection Required", "Please select an exam first.")
            return
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Eligible Candidates",
            "Enter candidate register numbers (one per line):",
        )
        if not ok:
            return
        ids = []
        missing = []
        for reg in [t.strip() for t in text.splitlines() if t.strip()]:
            stu = student_service.get_student_by_register_no(reg)
            (ids.append(stu["id"]) if stu else missing.append(reg))
        added = exam_service.set_eligible_students(exam["id"], ids)
        msg = f"Successfully registered {added} eligible student(s)."
        if missing:
            msg += f"\n\nNot found in directory: {', '.join(missing)}"
        QMessageBox.information(self, "Candidate Enrollment", msg)
        self._refresh_details()

    def _new_hall(self) -> None:
        name, ok = QInputDialog.getText(self, "New Examination Hall", "Hall name:")
        if not ok or not name.strip():
            return
        room, _ = QInputDialog.getText(self, "New Examination Hall", "Room identifier:")
        cap, ok = QInputDialog.getInt(self, "New Examination Hall", "Seat capacity:", 60, 1, 1000)
        if not ok:
            return
        exam_service.create_hall(name.strip(), room.strip(), cap)
        self._load_halls()

    def _generate_seats(self) -> None:
        hall_id = self.hall_combo.currentData()
        if not hall_id:
            QMessageBox.information(self, "Hall Required", "Select or create an examination hall first.")
            return
        count, ok = QInputDialog.getInt(self, "Generate Seats", "Number of seats to instantiate:", 60, 1, 500)
        if not ok:
            return
        created = exam_service.create_seats(hall_id, count)
        QMessageBox.information(self, "Seats Initialized", f"Generated {len(created)} seat positions.")
        self._refresh_details()

    def _allocate(self) -> None:
        exam = self._current_exam()
        if not exam:
            QMessageBox.information(self, "Exam Required", "Select an active exam session first.")
            return
        result = exam_service.allocate_seats(exam["id"])
        skipped = result["skipped"]
        msg = f"Auto-allocation completed: {result['assigned']} seat(s) assigned."
        if skipped:
            msg += f"\n\nSkipped {len(skipped)} students due to insufficient hall capacity."
        QMessageBox.information(self, "Seat Allocation Result", msg)
        self._refresh_details()

    def _refresh_details(self) -> None:
        exam = self._current_exam()
        if not exam:
            self.info_title.setText("No Exam Selected")
            self.info_details.setText("Select or create an examination session to configure halls and seating.")
            set_pill(self.pill_eligible, "0 Eligible", "info")
            set_pill(self.pill_allocated, "0 Allocated", "purple")
            set_pill(self.pill_verified, "0 Verified", "success")
            self.seats_table.setRowCount(0)
            return

        elig = exam_service.eligible_students(exam["id"])
        allocated = exam_service.allocations_for_exam(exam["id"])
        attended = exam_service.exam_attendance_rows(exam["id"])

        self.info_title.setText(f"{exam['exam_name']} — {exam['subject']}")
        self.info_details.setText(
            f"📅 Session Date: {exam['exam_date']}    🕒 Window: {exam['start_time']} – {exam['end_time']}"
        )
        set_pill(self.pill_eligible, f"{len(elig)} Eligible", "info")
        set_pill(self.pill_allocated, f"{len(allocated)} Allocated", "purple")
        set_pill(self.pill_verified, f"{len(attended)} Verified", "success")

        hall_id = self.hall_combo.currentData()
        if hall_id:
            seats = exam_service.seats_for_hall(hall_id)
            self.seats_table.setRowCount(len(seats))
            for r, seat in enumerate(seats):
                status_txt = seat["status"]
                icon = "🟢" if status_txt == "VACANT" else ("🔵" if status_txt == "ASSIGNED" else "🟣")
                self.seats_table.setItem(r, 0, QTableWidgetItem(f"🪑 {seat['seat_number']}"))
                self.seats_table.setItem(r, 1, QTableWidgetItem(f"{icon} {status_txt}"))
                self.seats_table.setItem(r, 2, QTableWidgetItem(seat["id"]))

    def _export_exam(self) -> None:
        exam = self._current_exam()
        if not exam:
            QMessageBox.information(self, "Selection Required", "Select an active exam first.")
            return
        from excel.excel_export import export_exam_attendance

        path = export_exam_attendance(exam)
        QMessageBox.information(
            self, "Report Exported", f"Exam attendance report generated:\n\n{path}"
        )


class ExamScanWidget(QWidget):
    """Futuristic exam hall kiosk: biometric scan → verify candidate eligibility → showcase hall/seat spotlight."""

    def __init__(self, parent=None, scanner_service: ScannerService | None = None) -> None:
        super().__init__(parent)
        self.scanner_service = scanner_service or ScannerService()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(18)

        # -------------------------------------------------------------
        # 1. Exam Session Selection Bar
        # -------------------------------------------------------------
        top = QHBoxLayout()
        top.setSpacing(12)

        lbl_exam = QLabel("VERIFICATION SESSION:")
        lbl_exam.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        top.addWidget(lbl_exam)

        self.exam_combo = QComboBox()
        self.exam_combo.setFixedHeight(40)
        top.addWidget(self.exam_combo, 2)

        self.start_btn = QPushButton("▶  Activate Biometric Gate Terminal")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self._start)
        top.addWidget(self.start_btn)

        root.addLayout(top)

        # -------------------------------------------------------------
        # 2. Main Terminal Spotlight Card
        # -------------------------------------------------------------
        terminal_card = QFrame()
        terminal_card.setObjectName("terminalCard")
        terminal_card.setStyleSheet(
            """
            QFrame#terminalCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #131E35, stop:1 #0F172A);
                border: 2px solid #283C66;
                border-radius: 16px;
            }
            """
        )
        t_lay = QVBoxLayout(terminal_card)
        t_lay.setContentsMargins(24, 24, 24, 24)
        t_lay.setSpacing(16)

        # Terminal Header
        term_header = QHBoxLayout()
        term_title = QLabel("🛡️  EXAM HALL BIOMETRIC VERIFICATION GATE")
        term_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #818CF8; letter-spacing: 1px;")
        term_header.addWidget(term_title)
        term_header.addStretch(1)

        self.gate_status_pill = StatusPill("GATE READY", "neutral")
        term_header.addWidget(self.gate_status_pill)
        t_lay.addLayout(term_header)

        # Verification Banner
        self.status_banner = QLabel("Select Active Exam and Place Registered Finger on Biometric Scanner")
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_banner.setStyleSheet(
            """
            background-color: #141E33;
            border: 1px solid #22314E;
            border-radius: 10px;
            padding: 12px;
            font-size: 15px;
            font-weight: 700;
            color: #94A3B8;
            """
        )
        t_lay.addWidget(self.status_banner)

        # Center Stage: Giant Seat & Candidate Spotlight
        self.spotlight_box = QFrame()
        self.spotlight_box.setObjectName("spotlightBox")
        self.spotlight_box.setStyleSheet(
            """
            QFrame#spotlightBox {
                background-color: #0A0F1D;
                border: 1px dashed #243555;
                border-radius: 12px;
            }
            """
        )
        sp_lay = QHBoxLayout(self.spotlight_box)
        sp_lay.setContentsMargins(24, 20, 24, 20)
        sp_lay.setSpacing(24)

        # Left: Candidate Credentials
        cand_lay = QVBoxLayout()
        cand_lay.setSpacing(6)
        cand_lbl = QLabel("CANDIDATE INFORMATION")
        cand_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.8px;")
        cand_lay.addWidget(cand_lbl)

        self.student_name = QLabel("—")
        self.student_name.setStyleSheet("font-size: 24px; font-weight: 800; color: #F8FAFC;")
        cand_lay.addWidget(self.student_name)

        self.student_reg = QLabel("Register No: —")
        self.student_reg.setStyleSheet("font-size: 14px; font-weight: 600; color: #818CF8;")
        cand_lay.addWidget(self.student_reg)

        self.student_extra = QLabel("Class / Department: —")
        self.student_extra.setStyleSheet("font-size: 12px; color: #94A3B8;")
        cand_lay.addWidget(self.student_extra)
        sp_lay.addLayout(cand_lay, 4)

        # Vertical separator
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.Shape.VLine)
        v_sep.setStyleSheet("color: #1E293B;")
        sp_lay.addWidget(v_sep)

        # Right: Giant Seat Spotlight Box
        seat_box = QVBoxLayout()
        seat_box.setSpacing(6)

        seat_hdr = QLabel("ALLOCATED SEAT")
        seat_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        seat_hdr.setStyleSheet("font-size: 11px; font-weight: 800; color: #38BDF8; letter-spacing: 1px;")
        seat_box.addWidget(seat_hdr)

        self.seat_number = QLabel("—")
        self.seat_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.seat_number.setStyleSheet(
            """
            font-size: 28px;
            font-weight: 800;
            color: #38BDF8;
            letter-spacing: 0.5px;
            padding: 2px 8px;
            """
        )
        seat_box.addWidget(self.seat_number)

        self.hall_info = QLabel("Hall: —")
        self.hall_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hall_info.setStyleSheet("font-size: 13px; font-weight: 600; color: #CBD5E1;")
        seat_box.addWidget(self.hall_info)

        sp_lay.addLayout(seat_box, 3)
        t_lay.addWidget(self.spotlight_box)

        # Timestamp pill
        self.time_stamp_lbl = QLabel("")
        self.time_stamp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_stamp_lbl.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 600;")
        t_lay.addWidget(self.time_stamp_lbl)

        root.addWidget(terminal_card, 1)

        # Compatibility text reference
        self.display = self.status_banner

        # Scanner bridge
        self.scan_bridge = ScanBridge(self.scanner_service, self)
        self.scan_bridge.scanned.connect(self._on_scan)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.exam_combo.blockSignals(True)
        self.exam_combo.clear()
        for ex in exam_service.list_exams():
            self.exam_combo.addItem(f"{ex['exam_name']} ({ex['exam_date']})", ex["id"])
        self.exam_combo.blockSignals(False)

    def _start(self) -> None:
        if not self.exam_combo.currentData():
            QMessageBox.warning(self, "Exam Required", "Please select an examination session first.")
            return
        self.status_banner.setText("⚡ Biometric Gate Active — Waiting for Candidate Fingerprint…")
        self.status_banner.setStyleSheet(
            """
            background-color: rgba(99, 102, 241, 0.15);
            border: 1px solid #6366F1;
            border-radius: 10px;
            padding: 12px;
            font-size: 15px;
            font-weight: 700;
            color: #A5B4FC;
            """
        )
        set_pill(self.gate_status_pill, "GATE ACTIVE", "primary")
        self.start_btn.setText("⚡ Gate Listening (Scanner Active)")
        self.scanner_service.start()

    def _on_scan(self, event: ScanEvent) -> None:
        from fingerprint.verification import VerificationService

        result = VerificationService(self.scanner_service).identify_event(event)
        if not result.success:
            self._show_error("UNKNOWN BIOMETRIC TEMPLATE", "Fingerprint not recognized. Candidate must report to the Invigilator.")
            return

        exam_id = self.exam_combo.currentData()
        outcome = exam_service.mark_exam_present(exam_id, result.student)
        student = result.student

        if not outcome["ok"]:
            self._show_ineligible(
                student,
                outcome.get("reason", "NOT ELIGIBLE FOR THIS EXAM"),
                outcome.get("detail", "Student is not enrolled on the candidate roster for this session."),
            )
            return

        alloc = outcome["allocation"]
        halls = {h["id"]: h for h in exam_service.list_halls()}
        seats = {s["id"]: s for s in exam_service.seats_for_hall(alloc["hall_id"])}
        exam = self._current_exam()
        hall_name = halls.get(alloc["hall_id"], {}).get("hall_name", "Hall 1")
        seat_no = seats.get(alloc["seat_id"], {}).get("seat_number", "?")

        now_str = datetime.now().strftime("%I:%M:%S %p")
        if outcome["duplicate"]:
            self._show_duplicate(student, hall_name, seat_no, now_str)
        else:
            self._show_admitted(student, hall_name, seat_no, now_str)

    def _show_admitted(self, student: dict, hall: str, seat: str, t: str) -> None:
        self.status_banner.setText("✔  ENTRY PERMITTED — CANDIDATE VERIFIED & ADMITTED")
        self.status_banner.setStyleSheet(
            """
            background-color: rgba(16, 185, 129, 0.2);
            border: 2px solid #10B981;
            border-radius: 10px;
            padding: 12px;
            font-size: 16px;
            font-weight: 800;
            color: #34D399;
            """
        )
        set_pill(self.gate_status_pill, "ADMISSION GRANTED", "success")

        self.student_name.setText(student["name"])
        self.student_reg.setText(f"Register No: {student['register_no']}")
        self.student_extra.setText(f"Class: {student.get('class', '—')}   •   Dept: {student.get('department', '—')}")

        self.seat_number.setText(f"SEAT {seat}")
        self.hall_info.setText(f"🏛️ {hall}")
        self.time_stamp_lbl.setText(f"Biometric Verification Logged: {t}")

    def _show_duplicate(self, student: dict, hall: str, seat: str, t: str) -> None:
        self.status_banner.setText("⚠️  DUPLICATE SCAN — CANDIDATE ALREADY ADMITTED TO HALL")
        self.status_banner.setStyleSheet(
            """
            background-color: rgba(245, 158, 11, 0.2);
            border: 2px solid #F59E0B;
            border-radius: 10px;
            padding: 12px;
            font-size: 16px;
            font-weight: 800;
            color: #FBBF24;
            """
        )
        set_pill(self.gate_status_pill, "ALREADY VERIFIED", "warning")

        self.student_name.setText(student["name"])
        self.student_reg.setText(f"Register No: {student['register_no']}")
        self.student_extra.setText(f"Class: {student.get('class', '—')}   •   Dept: {student.get('department', '—')}")

        self.seat_number.setText(f"SEAT {seat}")
        self.hall_info.setText(f"🏛️ {hall}")
        self.time_stamp_lbl.setText(f"Candidate was previously logged at: {t}")

    def _show_ineligible(self, student: dict, reason: str, detail: str) -> None:
        self.status_banner.setText(f"✖  ADMISSION DENIED — {reason}")
        self.status_banner.setStyleSheet(
            """
            background-color: rgba(239, 68, 68, 0.2);
            border: 2px solid #EF4444;
            border-radius: 10px;
            padding: 12px;
            font-size: 16px;
            font-weight: 800;
            color: #F87171;
            """
        )
        set_pill(self.gate_status_pill, "ADMISSION DENIED", "danger")

        self.student_name.setText(student["name"])
        self.student_reg.setText(f"Register No: {student['register_no']}")
        self.student_extra.setText(detail)

        self.seat_number.setText("NO SEAT")
        self.hall_info.setText("Hall: Not Allocated")
        self.time_stamp_lbl.setText("Candidate is not eligible for this examination hall.")

    def _show_error(self, title: str, subtitle: str) -> None:
        self.status_banner.setText(f"✖  {title}")
        self.status_banner.setStyleSheet(
            """
            background-color: rgba(239, 68, 68, 0.2);
            border: 2px solid #EF4444;
            border-radius: 10px;
            padding: 12px;
            font-size: 16px;
            font-weight: 800;
            color: #F87171;
            """
        )
        set_pill(self.gate_status_pill, "UNKNOWN TEMPLATE", "danger")

        self.student_name.setText("Unrecognized Fingerprint")
        self.student_reg.setText("Register No: —")
        self.student_extra.setText(subtitle)

        self.seat_number.setText("—")
        self.hall_info.setText("Hall: —")
        self.time_stamp_lbl.setText("Biometric sensor recorded unmatched template.")

    def _current_exam(self) -> dict | None:
        exid = self.exam_combo.currentData()
        for ex in exam_service.list_exams():
            if ex["id"] == exid:
                return ex
        return None
