"""Admin login dialog with high-contrast Obsidian & Sapphire branding."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from database.auth import login


class LoginDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SmartAttend — Secure Admin Access")
        self.setFixedWidth(460)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)

        logo_path = Path(__file__).resolve().parent.parent / "assets" / "grt_logo.png"
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        self.admin: dict | None = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # -------------------------------------------------------------
        # Institutional Header Banner
        # -------------------------------------------------------------
        banner_container = QFrame()
        banner_container.setStyleSheet(
            """
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
            }
            """
        )
        banner_layout = QVBoxLayout(banner_container)
        banner_layout.setContentsMargins(6, 6, 6, 6)
        banner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        banner_label = QLabel()
        banner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner_path = Path(__file__).resolve().parent.parent / "assets" / "college_banner.jpg"
        if banner_path.exists():
            pix = QPixmap(str(banner_path))
            if not pix.isNull():
                scaled = pix.scaledToWidth(390, Qt.TransformationMode.SmoothTransformation)
                banner_label.setPixmap(scaled)

        banner_layout.addWidget(banner_label)
        main_layout.addWidget(banner_container, 0, Qt.AlignmentFlag.AlignCenter)

        # -------------------------------------------------------------
        # Form Container
        # -------------------------------------------------------------
        form_frame = QFrame()
        form_frame.setObjectName("loginCard")
        form_frame.setStyleSheet(
            """
            QFrame#loginCard {
                background-color: #141E33;
                border: 1px solid #22314E;
                border-radius: 14px;
            }
            """
        )
        form_lay = QVBoxLayout(form_frame)
        form_lay.setContentsMargins(20, 20, 20, 20)
        form_lay.setSpacing(14)

        # Username
        u_label = QLabel("USERNAME")
        u_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        form_lay.addWidget(u_label)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Enter administrator username")
        self.username.setText("admin")
        self.username.setFixedHeight(40)
        form_lay.addWidget(self.username)

        # Password
        p_label = QLabel("PASSWORD")
        p_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;")
        form_lay.addWidget(p_label)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Enter admin password")
        self.password.setText("admin123")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedHeight(40)
        self.password.returnPressed.connect(self._try_login)
        form_lay.addWidget(self.password)

        # Error notification banner (hidden by default)
        self.error_badge = QLabel("")
        self.error_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_badge.setStyleSheet(
            """
            background-color: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.35);
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 12px;
            font-weight: 600;
            """
        )
        self.error_badge.setVisible(False)
        form_lay.addWidget(self.error_badge)

        main_layout.addWidget(form_frame)

        # -------------------------------------------------------------
        # Quick Demo Fill Action
        # -------------------------------------------------------------
        demo_btn = QPushButton("⚡ Auto-Fill Demo Credentials (admin / admin123)")
        demo_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px dashed #334155;
                color: #818CF8;
                border-radius: 8px;
                padding: 6px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.1);
                border-color: #6366F1;
                color: #A5B4FC;
            }
            """
        )
        demo_btn.clicked.connect(self._fill_demo)
        main_layout.addWidget(demo_btn)

        # -------------------------------------------------------------
        # Action Buttons
        # -------------------------------------------------------------
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        login_btn = QPushButton("Sign In to Console")
        login_btn.setObjectName("primaryBtn")
        login_btn.setFixedHeight(42)
        login_btn.clicked.connect(self._try_login)
        actions_layout.addWidget(login_btn)

        cancel_btn = QPushButton("Exit Application")
        cancel_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #64748B;
                font-size: 12px;
                padding: 6px;
            }
            QPushButton:hover {
                color: #94A3B8;
            }
            """
        )
        cancel_btn.clicked.connect(self.reject)
        actions_layout.addWidget(cancel_btn)

        main_layout.addLayout(actions_layout)

    def _fill_demo(self) -> None:
        self.username.setText("admin")
        self.password.setText("admin123")
        self.error_badge.setVisible(False)

    def _try_login(self) -> None:
        user = self.username.text().strip()
        pwd = self.password.text()

        if not user or not pwd:
            self.error_badge.setText("Please enter both username and password.")
            self.error_badge.setVisible(True)
            return

        admin = login(user, pwd)
        if admin:
            self.admin = admin
            self.accept()
        else:
            self.error_badge.setText("Invalid credentials. Try admin / admin123")
            self.error_badge.setVisible(True)
