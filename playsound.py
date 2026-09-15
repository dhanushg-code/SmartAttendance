"""Compatibility wrapper for playsound using playsound3 with fallback."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from playsound3 import playsound as _playsound3
    def playsound(sound: str, block: bool = True) -> None:
        try:
            _playsound3(sound, block=block)
        except Exception as exc:
            logger.warning("playsound3 playback error (%s), using system beep", exc)
            _fallback_beep()
except ImportError:
    try:
        from playsound import playsound as _playsound_orig
        def playsound(sound: str, block: bool = True) -> None:
            try:
                _playsound_orig(sound, block=block)
            except Exception as exc:
                logger.warning("playsound playback error (%s), using system beep", exc)
                _fallback_beep()
    except ImportError:
        def playsound(sound: str, block: bool = True) -> None:
            _fallback_beep()


def _fallback_beep() -> None:
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass
