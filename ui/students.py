"""Student management UI: add/edit/delete + biometric enrollment + real-time search."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import students as student_service
from fingerprint.enrollment import EnrollmentError
from fingerprint.scanner import ScannerService
from ui.common import StatusPill, set_pill


class StudentDialog(QDialog):
    """Add or edit a student; optionally register a fingerprint."""

    def __init__(
        self,
        parent=None,
        student: dict | None = None,
        scanner_service: ScannerService | None = None,
    ) -> None:
        super().__init__(parent)
        self.student = student
        self.scanner_service = scanner_service or ScannerService()
        self.template_id: str | None = None
        editing = student is not None

        self.setWindowTitle("Edit Student Profile" if editing else "Enroll New Student")
        self.setFixedWidth(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        head_box = QVBoxLayout()
        head_box.setSpacing(2)
        head_title = QLabel("Student Profile" if editing else "Student Registration")
        head_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        head_sub = QLabel("Academic credentials and biometric identification parameters.")
        head_sub.setStyleSheet("font-size: 12px; color: #94A3B8;")
        head_box.addWidget(head_title)
        head_box.addWidget(head_sub)
        root.addLayout(head_box)

        # Form Card
        card = QFrame()
        card.setObjectName("formCard")
        card.setStyleSheet(
            """
            QFrame#formCard {
                background-color: #141E33;
                border: 1px solid #22314E;
                border-radius: 12px;
            }
            """
        )
        form = QVBoxLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setSpacing(12)

        # Register No & Name Row
        r1 = QHBoxLayout()
        r1.setSpacing(12)

        box_reg = QVBoxLayout()
        lbl_reg = QLabel("REGISTER NO *")
        lbl_reg.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.register_no = QLineEdit()
        self.register_no.setPlaceholderText("e.g. 2024CS101")
        box_reg.addWidget(lbl_reg)
        box_reg.addWidget(self.register_no)
        r1.addLayout(box_reg, 1)

        box_name = QVBoxLayout()
        lbl_name = QLabel("FULL NAME *")
        lbl_name.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. Alex Rivera")
        box_name.addWidget(lbl_name)
        box_name.addWidget(self.name)
        r1.addLayout(box_name, 1)

        form.addLayout(r1)

        # Class & Department Row
        r2 = QHBoxLayout()
        r2.setSpacing(12)

        box_class = QVBoxLayout()
        lbl_class = QLabel("CLASS / SECTION *")
        lbl_class.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.sclass = QComboBox()
        self.sclass.setEditable(True)
        self.sclass.addItems(["CSE-A", "CSE-B", "ECE-A", "ECE-B", "IT-A", "MECH-A"])
        box_class.addWidget(lbl_class)
        box_class.addWidget(self.sclass)
        r2.addLayout(box_class, 1)

        box_dept = QVBoxLayout()
        lbl_dept = QLabel("DEPARTMENT *")
        lbl_dept.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.department = QComboBox()
        self.department.setEditable(True)
        self.department.addItems(["CSE", "ECE", "IT", "MECH", "CIVIL"])
        box_dept.addWidget(lbl_dept)
        box_dept.addWidget(self.department)
        r2.addLayout(box_dept, 1)

        form.addLayout(r2)

        # Email & Phone Row
        r3 = QHBoxLayout()
        r3.setSpacing(12)

        box_email = QVBoxLayout()
        lbl_email = QLabel("EMAIL ADDRESS")
        lbl_email.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.email = QLineEdit()
        self.email.setPlaceholderText("student@university.edu")
        box_email.addWidget(lbl_email)
        box_email.addWidget(self.email)
        r3.addLayout(box_email, 1)

        box_phone = QVBoxLayout()
        lbl_phone = QLabel("PHONE NUMBER")
        lbl_phone.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+1 234 567 8900")
        box_phone.addWidget(lbl_phone)
        box_phone.addWidget(self.phone)
        r3.addLayout(box_phone, 1)

        form.addLayout(r3)
        root.addWidget(card)

        # Biometric Scanner Card
        fp_card = QFrame()
        fp_card.setObjectName("fpCard")
        fp_card.setStyleSheet(
            """
            QFrame#fpCard {
                background-color: #0F172A;
                border: 1px solid #22314E;
                border-radius: 12px;
            }
            """
        )
        fp_lay = QHBoxLayout(fp_card)
        fp_lay.setContentsMargins(16, 14, 16, 14)
        fp_lay.setSpacing(14)

        fp_icon = QLabel("🔘")
        fp_icon.setStyleSheet("font-size: 24px;")
        fp_lay.addWidget(fp_icon)

        fp_info = QVBoxLayout()
        fp_info.setSpacing(2)
        fp_title = QLabel("BIOMETRIC FINGERPRINT")
        fp_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.fp_status = QLabel("Not registered yet")
        self.fp_status.setStyleSheet("font-size: 13px; font-weight: 600; color: #CBD5E1;")
        fp_info.addWidget(fp_title)
        fp_info.addWidget(self.fp_status)
        fp_lay.addLayout(fp_info, 1)

        fp_btn = QPushButton("Scan Fingerprint")
        fp_btn.setFixedHeight(36)
        fp_btn.clicked.connect(self._scan_fingerprint)
        fp_lay.addWidget(fp_btn)

        root.addWidget(fp_card)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Student")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        btn_box.addWidget(save_btn)

        root.addLayout(btn_box)

        # Prepopulate if editing
        if editing and student:
            self.register_no.setText(student["register_no"])
            self.register_no.setEnabled(False)
            self.name.setText(student["name"])
            self.sclass.setCurrentText(student["class"])
            self.department.setCurrentText(student["department"])
            self.email.setText(student.get("email") or "")
            self.phone.setText(student.get("phone") or "")
            if student.get("fingerprint_id"):
                self.fp_status.setText(f"Enrolled (Template ID #{student['fingerprint_id']})")
                self.fp_status.setStyleSheet("font-size: 13px; font-weight: 700; color: #34D399;")
                self.template_id = student["fingerprint_id"]

    def _scan_fingerprint(self) -> None:
        try:
            self.template_id = self.scanner_service.capture_once().template_id
        except Exception as exc:
            QMessageBox.warning(self, "Scanner Error", f"Biometric capture failed:\n{exc}")
            return
        if self.template_id:
            self.fp_status.setText(f"Captured Successfully (Template #{self.template_id})")
            self.fp_status.setStyleSheet("font-size: 13px; font-weight: 700; color: #34D399;")

    def _save(self) -> None:
        register_no = self.register_no.text().strip()
        name = self.name.text().strip()
        if not register_no or not name:
            QMessageBox.warning(self, "Incomplete Form", "Register number and name are mandatory.")
            return
        try:
            if self.student:
                student_service.update_student(
                    self.student["id"],
                    name=name,
                    **{"class": self.sclass.currentText().strip()},
                    department=self.department.currentText().strip(),
                    email=self.email.text().strip(),
                    phone=self.phone.text().strip(),
                )
                sid = self.student["id"]
            else:
                row = student_service.add_student(
                    register_no,
                    name,
                    self.sclass.currentText().strip(),
                    self.department.currentText().strip(),
                    self.email.text().strip(),
                    self.phone.text().strip(),
                )
                sid = row["id"]
            if self.template_id:
                student_service.set_fingerprint(sid, self.template_id)
        except (student_service.StudentError, EnrollmentError) as exc:
            QMessageBox.warning(self, "Database Error", str(exc))
            return
        self.accept()


class StudentsWidget(QWidget):
    def __init__(self, parent=None, scanner_service: ScannerService | None = None) -> None:
        super().__init__(parent)
        self.scanner_service = scanner_service or ScannerService()
        self._all_students: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # -------------------------------------------------------------
        # Filter & Action Bar
        # -------------------------------------------------------------
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        # Search field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search student by name or register number…")
        self.search_input.setFixedHeight(38)
        self.search_input.textChanged.connect(self._apply_filter)
        action_bar.addWidget(self.search_input, 2)

        # Department Filter
        self.dept_filter = QComboBox()
        self.dept_filter.setFixedHeight(38)
        self.dept_filter.addItem("All Departments", "")
        for d in ("CSE", "ECE", "IT", "MECH", "CIVIL"):
            self.dept_filter.addItem(f"Dept: {d}", d)
        self.dept_filter.currentIndexChanged.connect(self._apply_filter)
        action_bar.addWidget(self.dept_filter, 1)

        # Buttons
        add_btn = QPushButton("➕ Add Student")
        add_btn.setObjectName("primaryBtn")
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self._add)
        action_bar.addWidget(add_btn)

        edit_btn = QPushButton("✏️ Edit")
        edit_btn.setFixedHeight(38)
        edit_btn.clicked.connect(self._edit)
        action_bar.addWidget(edit_btn)

        del_btn = QPushButton("🗑️ Delete")
        del_btn.setObjectName("dangerBtn")
        del_btn.setFixedHeight(38)
        del_btn.clicked.connect(self._delete)
        action_bar.addWidget(del_btn)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedHeight(38)
        refresh_btn.clicked.connect(self.refresh)
        action_bar.addWidget(refresh_btn)

        root.addLayout(action_bar)

        # -------------------------------------------------------------
        # Summary Header Strip
        # -------------------------------------------------------------
        summary_strip = QHBoxLayout()
        summary_title = QLabel("STUDENTS DIRECTORY")
        summary_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        summary_strip.addWidget(summary_title)
        summary_strip.addStretch(1)

        self.count_pill = StatusPill("0 Students", "neutral")
        summary_strip.addWidget(self.count_pill)
        root.addLayout(summary_strip)

        # -------------------------------------------------------------
        # Modern Students Table
        # -------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Register No", "Student Name", "Class", "Department", "Biometric Status", "ID"]
        )
        self.table.setColumnHidden(5, True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        self.refresh()

    def refresh(self) -> None:
        self._all_students = student_service.list_students()
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.search_input.text().strip().lower()
        dept = self.dept_filter.currentData() or ""

        filtered = []
        for s in self._all_students:
            matches_query = (
                not query
                or query in s["name"].lower()
                or query in s["register_no"].lower()
            )
            matches_dept = not dept or s["department"] == dept
            if matches_query and matches_dept:
                filtered.append(s)

        self.table.setRowCount(len(filtered))
        for r, stu in enumerate(filtered):
            fp_id = stu.get("fingerprint_id")
            fp_text = f"🟢 Enrolled (#{fp_id})" if fp_id else "⚪ Unregistered"

            self.table.setItem(r, 0, QTableWidgetItem(stu["register_no"]))
            self.table.setItem(r, 1, QTableWidgetItem(stu["name"]))
            self.table.setItem(r, 2, QTableWidgetItem(stu["class"]))
            self.table.setItem(r, 3, QTableWidgetItem(stu["department"]))
            self.table.setItem(r, 4, QTableWidgetItem(fp_text))
            self.table.setItem(r, 5, QTableWidgetItem(stu["id"]))

        set_pill(self.count_pill, f"Showing {len(filtered)} of {len(self._all_students)} Students", "neutral")

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        sid = self.table.item(row, 5).text()
        return student_service.get_student(sid)

    def _add(self) -> None:
        dlg = StudentDialog(self, scanner_service=self.scanner_service)
        if dlg.exec():
            self.refresh()

    def _edit(self) -> None:
        stu = self._selected()
        if not stu:
            QMessageBox.information(self, "Selection Required", "Please select a student row from the table first.")
            return
        dlg = StudentDialog(self, student=stu, scanner_service=self.scanner_service)
        if dlg.exec():
            self.refresh()

    def _delete(self) -> None:
        stu = self._selected()
        if not stu:
            QMessageBox.information(self, "Selection Required", "Please select a student row from the table first.")
            return
        confirm = QMessageBox.question(
            self,
            "Confirm Student Deletion",
            f"Are you sure you want to delete {stu['name']} ({stu['register_no']})?\n\nThis will remove all associated biometric credentials.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            student_service.delete_student(stu["id"])
            self.refresh()
