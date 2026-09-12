"""SmartAttend entry point.

Run:  python main.py
Demo: DEMO_MODE=true (default without .env) — admin/admin123, simulated scanner.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from config import settings
from ui.common import apply_app_style
from ui.login import LoginDialog
from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    apply_app_style(app)

    problems = settings.validate()
    if problems:
        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("Configuration issues detected — continue in demo mode?")
        box.setDetailedText("\n".join(problems))
        box.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if box.exec() != QMessageBox.StandardButton.Yes:
            return 1
        settings.DEMO_MODE = True

    if settings.DEMO_MODE:
        try:
            from scripts.seed_demo import main as seed_demo
            seed_demo()
        except Exception:
            pass

    login = LoginDialog()
    if login.exec() != LoginDialog.DialogCode.Accepted or not login.admin:
        return 0

    window = MainWindow(login.admin)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
