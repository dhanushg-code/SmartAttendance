"""Staff management UI: add/edit/delete + search, mirroring students.py."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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

from database import staff as staff_service
from ui.common import StatusPill, set_pill


class StaffDialog(QDialog):
    """Add or edit a faculty/staff profile."""

    def __init__(self, parent=None, staff: dict | None = None) -> None:
        super().__init__(parent)
        self.staff = staff
        editing = staff is not None

        self.setWindowTitle("Edit Faculty Profile" if editing else "Register Faculty Member")
        self.setFixedWidth(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Header
        head_box = QVBoxLayout()
        head_box.setSpacing(2)
        head_title = QLabel("Faculty Profile" if editing else "Faculty Registration")
        head_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #F8FAFC;")
        head_sub = QLabel("Academic staff credentials, contact info, and alert endpoints.")
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

        # Full Name
        box_name = QVBoxLayout()
        lbl_name = QLabel("FULL NAME *")
        lbl_name.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. Dr. Alan Turing")
        box_name.addWidget(lbl_name)
        box_name.addWidget(self.name)
        form.addLayout(box_name)

        # Email & Phone Row
        r1 = QHBoxLayout()
        r1.setSpacing(12)

        box_email = QVBoxLayout()
        lbl_email = QLabel("EMAIL ADDRESS (FOR ALERTS)")
        lbl_email.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.email = QLineEdit()
        self.email.setPlaceholderText("faculty@university.edu")
        box_email.addWidget(lbl_email)
        box_email.addWidget(self.email)
        r1.addLayout(box_email, 1)

        box_phone = QVBoxLayout()
        lbl_phone = QLabel("PHONE NUMBER")
        lbl_phone.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("+1 234 567 8900")
        box_phone.addWidget(lbl_phone)
        box_phone.addWidget(self.phone)
        r1.addLayout(box_phone, 1)

        form.addLayout(r1)

        # Device Token
        box_token = QVBoxLayout()
        lbl_token = QLabel("DEVICE TOKEN (PUSH NOTIFICATIONS)")
        lbl_token.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.6px;")
        self.device_token = QLineEdit()
        self.device_token.setPlaceholderText("e.g. fcm_token_xyz123 or device-id")
        box_token.addWidget(lbl_token)
        box_token.addWidget(self.device_token)
        form.addLayout(box_token)

        root.addWidget(card)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(38)
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Staff")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        btn_box.addWidget(save_btn)

        root.addLayout(btn_box)

        # Prepopulate if editing
        if editing and staff:
            self.name.setText(staff.get("name") or "")
            self.email.setText(staff.get("email") or "")
            self.phone.setText(staff.get("phone") or "")
            self.device_token.setText(staff.get("device_token") or "")

    def _save(self) -> None:
        name = self.name.text().strip()
        email = self.email.text().strip()
        phone = self.phone.text().strip()
        device_token = self.device_token.text().strip()

        if not name:
            QMessageBox.warning(self, "Incomplete Form", "Staff full name is mandatory.")
            return

        try:
            if self.staff:
                staff_service.update_staff(
                    self.staff["id"],
                    name=name,
                    email=email or None,
                    phone=phone or None,
                    device_token=device_token or None,
                )
            else:
                staff_service.add_staff(
                    name=name,
                    email=email,
                    phone=phone,
                    device_token=device_token,
                )
        except staff_service.StaffError as exc:
            QMessageBox.warning(self, "Database Error", str(exc))
            return

        self.accept()


class StaffWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._all_staff: list[dict] = []

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
        self.search_input.setPlaceholderText("🔍  Search staff by name, email, or phone…")
        self.search_input.setFixedHeight(38)
        self.search_input.textChanged.connect(self._apply_filter)
        action_bar.addWidget(self.search_input, 2)

        # Buttons
        add_btn = QPushButton("➕ Add Staff")
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
        summary_title = QLabel("FACULTY & STAFF DIRECTORY")
        summary_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        summary_strip.addWidget(summary_title)
        summary_strip.addStretch(1)

        self.count_pill = StatusPill("0 Staff", "neutral")
        summary_strip.addWidget(self.count_pill)
        root.addLayout(summary_strip)

        # -------------------------------------------------------------
        # Modern Staff Table
        # -------------------------------------------------------------
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Staff Name", "Email Address", "Phone Number", "Device Token", "ID"]
        )
        self.table.setColumnHidden(4, True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        self.refresh()

    def refresh(self) -> None:
        self._all_staff = staff_service.list_staff()
        self._apply_filter()

    def _apply_filter(self) -> None:
        query = self.search_input.text().strip().lower()

        filtered = []
        for s in self._all_staff:
            name_m = query in (s.get("name") or "").lower()
            email_m = query in (s.get("email") or "").lower()
            phone_m = query in (s.get("phone") or "").lower()
            if not query or name_m or email_m or phone_m:
                filtered.append(s)

        self.table.setRowCount(len(filtered))
        for r, stf in enumerate(filtered):
            self.table.setItem(r, 0, QTableWidgetItem(stf.get("name") or ""))
            self.table.setItem(r, 1, QTableWidgetItem(stf.get("email") or "—"))
            self.table.setItem(r, 2, QTableWidgetItem(stf.get("phone") or "—"))
            token = stf.get("device_token") or "—"
            self.table.setItem(r, 3, QTableWidgetItem(token))
            self.table.setItem(r, 4, QTableWidgetItem(stf.get("id") or ""))

        set_pill(self.count_pill, f"Showing {len(filtered)} of {len(self._all_staff)} Staff", "neutral")

    def _selected(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        sid = self.table.item(row, 4).text()
        return staff_service.get_staff(sid)

    def _add(self) -> None:
        dlg = StaffDialog(self)
        if dlg.exec():
            self.refresh()

    def _edit(self) -> None:
        stf = self._selected()
        if not stf:
            QMessageBox.information(self, "Selection Required", "Please select a staff row from the table first.")
            return
        dlg = StaffDialog(self, staff=stf)
        if dlg.exec():
            self.refresh()

    def _delete(self) -> None:
        stf = self._selected()
        if not stf:
            QMessageBox.information(self, "Selection Required", "Please select a staff row from the table first.")
            return
        confirm = QMessageBox.question(
            self,
            "Confirm Staff Deletion",
            f"Are you sure you want to delete {stf['name']}?\n\nThis will remove faculty records from the system.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            staff_service.delete_staff(stf["id"])
            self.refresh()
