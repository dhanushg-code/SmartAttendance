"""Shared UI helpers and modern Obsidian & Sapphire design system for SmartAttend Qt widgets."""
from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fingerprint.scanner import ScannerService


class ScanBridge(QObject):
    """Marshals scanner worker-thread events onto the Qt main thread."""

    scanned = Signal(object)  # carries ScanEvent

    def __init__(self, scanner_service: ScannerService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = scanner_service
        self._service.on_scan(self._on_worker_event)

    def _on_worker_event(self, event) -> None:
        self.scanned.emit(event)


# ---------------------------------------------------------------------------
# Design System Color Tokens & Helper Badges
# ---------------------------------------------------------------------------

PALETTE = {
    "bg_void": "#0A0E17",
    "bg_main": "#0F172A",
    "bg_card": "#141E33",
    "bg_card_hover": "#1A2640",
    "border_subtle": "#1E293B",
    "border_card": "#22314E",
    "border_focus": "#6366F1",
    "sidebar_bg": "#0D1527",
    "sidebar_active": "#1E2C4F",
    "accent_primary": "#4F46E5",
    "accent_indigo": "#6366F1",
    "accent_cyan": "#06B6D4",
    "accent_emerald": "#10B981",
    "accent_amber": "#F59E0B",
    "accent_rose": "#EF4444",
    "accent_purple": "#8B5CF6",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
}


def StatusPill(text: str, variant: str = "info", parent: QWidget | None = None) -> QLabel:  # noqa: N802
    """Return a modern rounded chip badge with colored background and border."""
    lbl = QLabel(text, parent)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    styles = {
        "success": (
            "background-color: rgba(16, 185, 129, 0.16); "
            "color: #34D399; "
            "border: 1px solid rgba(16, 185, 129, 0.35);"
        ),
        "warning": (
            "background-color: rgba(245, 158, 11, 0.16); "
            "color: #FBBF24; "
            "border: 1px solid rgba(245, 158, 11, 0.35);"
        ),
        "danger": (
            "background-color: rgba(239, 68, 68, 0.16); "
            "color: #F87171; "
            "border: 1px solid rgba(239, 68, 68, 0.35);"
        ),
        "info": (
            "background-color: rgba(6, 182, 212, 0.16); "
            "color: #38BDF8; "
            "border: 1px solid rgba(6, 182, 212, 0.35);"
        ),
        "primary": (
            "background-color: rgba(99, 102, 241, 0.16); "
            "color: #A5B4FC; "
            "border: 1px solid rgba(99, 102, 241, 0.35);"
        ),
        "purple": (
            "background-color: rgba(139, 92, 246, 0.16); "
            "color: #C4B5FD; "
            "border: 1px solid rgba(139, 92, 246, 0.35);"
        ),
        "neutral": (
            "background-color: rgba(148, 163, 184, 0.12); "
            "color: #CBD5E1; "
            "border: 1px solid rgba(148, 163, 184, 0.25);"
        ),
    }
    style_rule = styles.get(variant, styles["neutral"])
    lbl.setFixedHeight(24)
    lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    lbl.setMinimumWidth(lbl.fontMetrics().horizontalAdvance(text) + 26)
    lbl.setStyleSheet(
        f"""
        {style_rule}
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        """
    )
    lbl.adjustSize()
    return lbl


def set_pill(lbl: QLabel, text: str, variant: str = "neutral") -> None:
    """Updates a StatusPill label text and color variant dynamically."""
    lbl.setText(text)
    styles = {
        "success": (
            "background-color: rgba(16, 185, 129, 0.16); "
            "color: #34D399; "
            "border: 1px solid rgba(16, 185, 129, 0.35);"
        ),
        "warning": (
            "background-color: rgba(245, 158, 11, 0.16); "
            "color: #FBBF24; "
            "border: 1px solid rgba(245, 158, 11, 0.35);"
        ),
        "danger": (
            "background-color: rgba(239, 68, 68, 0.16); "
            "color: #F87171; "
            "border: 1px solid rgba(239, 68, 68, 0.35);"
        ),
        "info": (
            "background-color: rgba(6, 182, 212, 0.16); "
            "color: #38BDF8; "
            "border: 1px solid rgba(6, 182, 212, 0.35);"
        ),
        "primary": (
            "background-color: rgba(99, 102, 241, 0.16); "
            "color: #A5B4FC; "
            "border: 1px solid rgba(99, 102, 241, 0.35);"
        ),
        "purple": (
            "background-color: rgba(139, 92, 246, 0.16); "
            "color: #C4B5FD; "
            "border: 1px solid rgba(139, 92, 246, 0.35);"
        ),
        "neutral": (
            "background-color: rgba(148, 163, 184, 0.12); "
            "color: #CBD5E1; "
            "border: 1px solid rgba(148, 163, 184, 0.25);"
        ),
    }
    style_rule = styles.get(variant, styles["neutral"])
    lbl.setFixedHeight(24)
    lbl.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    lbl.setMinimumWidth(lbl.fontMetrics().horizontalAdvance(text) + 26)
    lbl.setStyleSheet(
        f"""
        {style_rule}
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.3px;
        """
    )
    lbl.adjustSize()


def card(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    """A titled card container; returns (frame, body_layout). Backward-compatible."""
    frame = QFrame()
    frame.setObjectName("card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 18, 18, 18)
    lay.setSpacing(12)
    if title:
        header = QLabel(title)
        header.setObjectName("cardHeader")
        header.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.8px;"
        )
        lay.addWidget(header)
    return frame, lay


def form_row(label: str, placeholder: str = "") -> tuple[QHBoxLayout, QLineEdit]:
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setMinimumWidth(140)
    lbl.setStyleSheet("color: #CBD5E1; font-weight: 600; font-size: 13px;")
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    row.addWidget(lbl)
    row.addWidget(edit, 1)
    return row, edit


def big_status_label(text: str = "", color: str = "#F8FAFC") -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {color};")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def QtAlignCenter():  # noqa: N802
    return Qt.AlignmentFlag.AlignCenter


# ---------------------------------------------------------------------------
# Specialized Widgets: KPI Card & Biometric Scanner HUD
# ---------------------------------------------------------------------------

class StatCardWidget(QFrame):
    """Modern executive KPI Card with colored accent banner, icon, and trend label."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        icon_symbol: str = "📊",
        accent_color: str = "#6366F1",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setStyleSheet(
            f"""
            QFrame#kpiCard {{
                background-color: #141E33;
                border: 1px solid #22314E;
                border-top: 3px solid {accent_color};
                border-radius: 12px;
            }}
            QFrame#kpiCard:hover {{
                background-color: #17233D;
                border-color: #2F4268;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Top row: icon and title
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        icon_chip = QLabel(icon_symbol)
        icon_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_chip.setFixedSize(36, 36)
        icon_chip.setStyleSheet(
            f"""
            background-color: rgba({int(accent_color[1:3], 16)}, {int(accent_color[3:5], 16)}, {int(accent_color[5:7], 16)}, 0.15);
            color: {accent_color};
            border-radius: 8px;
            font-size: 18px;
            """
        )
        top_row.addWidget(icon_chip)

        self.title_label = QLabel(title.upper())
        self.title_label.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px;"
        )
        top_row.addWidget(self.title_label, 1)
        layout.addLayout(top_row)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            "font-size: 32px; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;"
        )
        layout.addWidget(self.value_label)

        # Subtitle
        self.sub_label = QLabel(subtitle)
        self.sub_label.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        layout.addWidget(self.sub_label)

    def set_value(self, val: str, subtitle: str | None = None) -> None:
        self.value_label.setText(val)
        if subtitle is not None:
            self.sub_label.setText(subtitle)


class BiometricScanHUD(QFrame):
    """High-tech biometric scanner display with reactive states (Idle, Scanning, Verified, etc.)."""

    def __init__(self, title: str = "Biometric Sensor", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("scannerHud")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        top = QHBoxLayout()
        header = QLabel(title.upper())
        header.setStyleSheet("font-size: 11px; font-weight: 700; color: #94A3B8; letter-spacing: 1px;")
        top.addWidget(header)
        top.addStretch(1)

        self.badge = StatusPill("SENSOR READY", "neutral")
        top.addWidget(self.badge)
        layout.addLayout(top)

        # Center graphic & message
        self.center_box = QFrame()
        self.center_box.setObjectName("hudCenter")
        c_lay = QVBoxLayout(self.center_box)
        c_lay.setContentsMargins(14, 16, 14, 16)
        c_lay.setSpacing(6)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel("⚡")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 32px;")
        c_lay.addWidget(self.icon_label)

        self.main_text = QLabel("Place Finger On Scanner")
        self.main_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_text.setStyleSheet("font-size: 18px; font-weight: 700; color: #F8FAFC;")
        c_lay.addWidget(self.main_text)

        self.sub_text = QLabel("Waiting for live biometric verification stream…")
        self.sub_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_text.setStyleSheet("font-size: 13px; color: #64748B;")
        c_lay.addWidget(self.sub_text)

        layout.addWidget(self.center_box)
        self.set_idle()

    def set_idle(self) -> None:
        self.setStyleSheet(
            """
            QFrame#scannerHud {
                background-color: #141E33;
                border: 1px solid #22314E;
                border-radius: 12px;
            }
            QFrame#hudCenter {
                background-color: #0F172A;
                border: 1px dashed #283754;
                border-radius: 10px;
            }
            """
        )
        set_pill(self.badge, "READY", "neutral")
        self.icon_label.setText("🔘")
        self.main_text.setText("Biometric Sensor Ready")
        self.main_text.setStyleSheet("font-size: 17px; font-weight: 700; color: #F8FAFC;")
        self.sub_text.setText("Place registered finger firmly on the optical scanner")
        self.sub_text.setStyleSheet("font-size: 13px; color: #94A3B8;")

    def set_scanning(self) -> None:
        self.setStyleSheet(
            """
            QFrame#scannerHud {
                background-color: #141E33;
                border: 1px solid #6366F1;
                border-radius: 12px;
            }
            QFrame#hudCenter {
                background-color: #101935;
                border: 1px solid #6366F1;
                border-radius: 10px;
            }
            """
        )
        set_pill(self.badge, "SCANNING…", "primary")
        self.icon_label.setText("⚡")
        self.main_text.setText("Capturing Biometric Template…")
        self.main_text.setStyleSheet("font-size: 17px; font-weight: 700; color: #818CF8;")
        self.sub_text.setText("Scanning ridge lines and cross-referencing database")
        self.sub_text.setStyleSheet("font-size: 13px; color: #A5B4FC;")

    def set_success(self, title: str, subtitle: str) -> None:
        self.setStyleSheet(
            """
            QFrame#scannerHud {
                background-color: #141E33;
                border: 1px solid #10B981;
                border-radius: 12px;
            }
            QFrame#hudCenter {
                background-color: rgba(16, 185, 129, 0.08);
                border: 1px solid #10B981;
                border-radius: 10px;
            }
            """
        )
        set_pill(self.badge, "VERIFIED", "success")
        self.icon_label.setText("✔")
        self.main_text.setText(title)
        self.main_text.setStyleSheet("font-size: 18px; font-weight: 800; color: #34D399;")
        self.sub_text.setText(subtitle)
        self.sub_text.setStyleSheet("font-size: 13px; color: #D1FAE5; font-weight: 500;")

    def set_duplicate(self, title: str, subtitle: str) -> None:
        self.setStyleSheet(
            """
            QFrame#scannerHud {
                background-color: #141E33;
                border: 1px solid #F59E0B;
                border-radius: 12px;
            }
            QFrame#hudCenter {
                background-color: rgba(245, 158, 11, 0.08);
                border: 1px solid #F59E0B;
                border-radius: 10px;
            }
            """
        )
        set_pill(self.badge, "DUPLICATE", "warning")
        self.icon_label.setText("⚠")
        self.main_text.setText(title)
        self.main_text.setStyleSheet("font-size: 17px; font-weight: 700; color: #FBBF24;")
        self.sub_text.setText(subtitle)
        self.sub_text.setStyleSheet("font-size: 13px; color: #FEF3C7;")

    def set_error(self, title: str, subtitle: str) -> None:
        self.setStyleSheet(
            """
            QFrame#scannerHud {
                background-color: #141E33;
                border: 1px solid #EF4444;
                border-radius: 12px;
            }
            QFrame#hudCenter {
                background-color: rgba(239, 68, 68, 0.08);
                border: 1px solid #EF4444;
                border-radius: 10px;
            }
            """
        )
        set_pill(self.badge, "REJECTED", "danger")
        self.icon_label.setText("✖")
        self.main_text.setText(title)
        self.main_text.setStyleSheet("font-size: 17px; font-weight: 700; color: #F87171;")
        self.sub_text.setText(subtitle)
        self.sub_text.setStyleSheet("font-size: 13px; color: #FEE2E2;")


# ---------------------------------------------------------------------------
# Global Application Stylesheet (Dark Obsidian & Sapphire)
# ---------------------------------------------------------------------------

def apply_app_style(app: QWidget | object) -> None:
    """Applies the master high-contrast Obsidian & Sapphire theme across all Qt widgets."""
    import os
    from PySide6.QtGui import QFont, QFontDatabase

    for f in ("segoeui.ttf", "segoeuib.ttf", "seguiemj.ttf", "arial.ttf"):
        p = os.path.join(r"C:\Windows\Fonts", f)
        if os.path.exists(p):
            QFontDatabase.addApplicationFont(p)

    if hasattr(app, "setFont"):
        app.setFont(QFont("Segoe UI", 10))

    app.setStyleSheet(
        """
        /* Master Window and Dialog Base */
        QMainWindow {
            background-color: #0A0E17;
            color: #F8FAFC;
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
            font-size: 13px;
        }
        QDialog {
            background-color: #0F172A;
            color: #F8FAFC;
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
            font-size: 13px;
        }
        QWidget {
            color: #F8FAFC;
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
        }

        /* Generic Cards and Panels */
        #card, QFrame#card {
            background-color: #141E33;
            border: 1px solid #1E293B;
            border-radius: 12px;
        }

        /* Push Buttons */
        QPushButton {
            background-color: #1E293B;
            color: #F8FAFC;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #28364F;
            border-color: #475569;
            color: #FFFFFF;
        }
        QPushButton:pressed {
            background-color: #182235;
        }
        QPushButton:disabled {
            background-color: #111827;
            color: #475569;
            border-color: #1E293B;
        }

        /* Primary Action Buttons */
        QPushButton#primaryBtn, QPushButton[default="true"] {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:1 #6366F1);
            color: #FFFFFF;
            border: 1px solid #6366F1;
            font-weight: 700;
        }
        QPushButton#primaryBtn:hover, QPushButton[default="true"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:1 #4F46E5);
            border-color: #818CF8;
        }
        QPushButton#successBtn {
            background-color: #059669;
            color: #FFFFFF;
            border: 1px solid #10B981;
            font-weight: 700;
        }
        QPushButton#successBtn:hover {
            background-color: #10B981;
        }
        QPushButton#dangerBtn {
            background-color: #DC2626;
            color: #FFFFFF;
            border: 1px solid #EF4444;
            font-weight: 700;
        }
        QPushButton#dangerBtn:hover {
            background-color: #EF4444;
        }

        /* Inputs and Text Edits */
        QLineEdit, QComboBox, QSpinBox, QDateEdit, QTimeEdit {
            background-color: #0F172A;
            border: 1px solid #283548;
            border-radius: 8px;
            padding: 8px 12px;
            color: #F8FAFC;
            font-size: 13px;
            selection-background-color: #4F46E5;
            selection-color: #FFFFFF;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {
            border: 1px solid #6366F1;
            background-color: #121C33;
        }
        QLineEdit:disabled, QComboBox:disabled {
            background-color: #0B101D;
            color: #475569;
            border-color: #1A2234;
        }

        /* Dropdown Combobox */
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid #283548;
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #94A3B8;
            width: 0;
            height: 0;
            margin-right: 6px;
        }
        QComboBox QAbstractItemView {
            background-color: #141E33;
            border: 1px solid #283548;
            border-radius: 8px;
            color: #F8FAFC;
            selection-background-color: #4F46E5;
            selection-color: #FFFFFF;
            padding: 4px;
            outline: none;
        }

        /* Table Widgets */
        QTableWidget {
            background-color: #141E33;
            alternate-background-color: #0F172A;
            border: 1px solid #1E293B;
            border-radius: 10px;
            gridline-color: #1C273C;
            color: #F1F5F9;
            font-size: 12px;
            selection-background-color: #263659;
            selection-color: #FFFFFF;
            outline: none;
        }
        QTableWidget::item {
            padding: 8px 10px;
            border-bottom: 1px solid #1A253A;
        }
        QTableWidget::item:selected {
            background-color: #263659;
            color: #FFFFFF;
        }
        QHeaderView::section {
            background-color: #0F172A;
            color: #94A3B8;
            padding: 8px 10px;
            border: none;
            border-bottom: 2px solid #22314E;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.6px;
            text-transform: uppercase;
        }

        /* Tab Widget (if used as fallback) */
        QTabWidget::pane {
            border: 1px solid #1E293B;
            border-radius: 8px;
            background: #0F172A;
            top: -1px;
        }
        QTabBar::tab {
            background: #141E33;
            color: #94A3B8;
            padding: 9px 20px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 600;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background: #4F46E5;
            color: #FFFFFF;
        }
        QTabBar::tab:hover:!selected {
            background: #1C273E;
            color: #E2E8F0;
        }

        /* Modern Scrollbars */
        QScrollBar:vertical {
            background-color: #0A0E17;
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background-color: #283750;
            min-height: 24px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #3B4E70;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            background-color: #0A0E17;
            height: 8px;
            margin: 0;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal {
            background-color: #283750;
            min-width: 24px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #3B4E70;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        /* Status Bar */
        QStatusBar {
            background-color: #0A0E17;
            color: #64748B;
            border-top: 1px solid #1E293B;
            font-size: 12px;
            font-weight: 500;
            padding: 4px 8px;
        }
        QStatusBar QLabel {
            color: #94A3B8;
        }

        /* Labels */
        QLabel {
            color: #F8FAFC;
        }
        """
    )
