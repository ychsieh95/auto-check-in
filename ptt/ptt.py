#!/usr/bin/env python3
"""
PttCheckin client: handles login and registration-status reporting for
PTT (批踢踢實業坊) via PyPtt.
"""

import json
import logging
from pathlib import Path

from i18n import normalize_lang, t
from PyPtt import PTT, connect_core, screens

log = logging.getLogger(__name__)


# PTT changed the status line on its main menu in August 2026.  PyPtt 2.3.6
# still looks for the old spacing/brackets, so it reaches the main menu and
# then raises LoginError.  Keep this narrowly guarded so a future PyPtt parser
# update is left untouched.
_STALE_MAIN_MENU_TARGET = ["離開，再見", "人, 我是", "[呼叫器]"]
# Keep only text shared by both of PTT's status-line layouts.  In particular,
# the compact layout has ``人,我是`` while the full layout has ``人, 我是``;
# matching ``人,我是`` therefore still rejects valid main-menu screens.
_CURRENT_MAIN_MENU_TARGET = ["離開，再見", "我是", "呼叫器"]
_SYNC_OUTPUT_MARKERS = (b"\x1b[?2026h", b"\x1b[?2026l")
_ORIGINAL_STREAM_SCREEN = connect_core.API._stream_screen


def _strip_synchronized_output_markers(data_chunk: bytes | str) -> bytes | str:
    for marker in _SYNC_OUTPUT_MARKERS:
        if isinstance(data_chunk, str):
            marker = marker.decode("ascii")
        data_chunk = data_chunk.replace(marker, b"" if isinstance(data_chunk, bytes) else "")
    return data_chunk


def _patch_pyptt_synchronized_output() -> None:
    """Keep PyPtt from freezing on PTT's synchronized-output control mode."""
    probe = screens.IncrementalScreen("utf-8")
    probe.feed(_SYNC_OUTPUT_MARKERS[0] + b"probe" + _SYNC_OUTPUT_MARKERS[1])
    if "probe" in probe.screen:
        return
    if getattr(connect_core.API._stream_screen, "_ptt_sync_compatible", False):
        return

    def compatible_stream_screen(self, encoding, data_chunk):
        return _ORIGINAL_STREAM_SCREEN(
            self, encoding, _strip_synchronized_output_markers(data_chunk)
        )

    compatible_stream_screen._ptt_sync_compatible = True
    connect_core.API._stream_screen = compatible_stream_screen


def _patch_pyptt_main_menu_target() -> None:
    """Teach affected PyPtt releases to recognize PTT's current main menu."""
    if screens.Target.MainMenu != _STALE_MAIN_MENU_TARGET:
        return

    screens.Target.MainMenu = _CURRENT_MAIN_MENU_TARGET.copy()

    # CursorToGoodbye is copied from MainMenu when PyPtt is imported.  Preserve
    # any cursor marker already appended by PyPtt while updating that prefix.
    prefix_length = len(_STALE_MAIN_MENU_TARGET)
    if screens.Target.CursorToGoodbye[:prefix_length] == _STALE_MAIN_MENU_TARGET:
        screens.Target.CursorToGoodbye = (
            _CURRENT_MAIN_MENU_TARGET.copy()
            + screens.Target.CursorToGoodbye[prefix_length:]
        )


class PttCheckin:
    """Client for logging into PTT and reporting account status."""

    def __init__(self, username: str, password: str, lang: str | None = None):
        self.username = username
        self.password = password
        self.lang = normalize_lang(lang)
        _patch_pyptt_main_menu_target()
        _patch_pyptt_synchronized_output()
        self.bot = PTT.API()

    @classmethod
    def from_config(cls, path: str | Path) -> "PttCheckin":
        """Build a client from a JSON config file with a 'ptt' section (username/password) and a top-level 'lang'."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        cfg = json.loads(config_path.read_text())
        ptt_cfg = cfg.get("ptt", {})
        missing = [k for k in ("username", "password") if not ptt_cfg.get(k)]
        if missing:
            raise ValueError(f"Config file missing required ptt key(s): {', '.join(missing)}")
        return cls(ptt_cfg["username"], ptt_cfg["password"], lang=cfg.get("lang"))

    def _(self, key: str, *args) -> str:
        """Translate a message key into the configured output language."""
        return t(self.lang, key, *args)

    def login(self, *, kick_other_session: bool = False) -> bool:
        """Log into PTT. Returns True on success."""
        try:
            self.bot.login(
                self.username,
                self.password,
                kick_other_session=kick_other_session,
            )
        except Exception as exc:
            log.warning(self._("ptt_login_failed", exc))
            self.close()
            return False
        log.info(self._("ptt_login_success", self.username))
        return True

    def close(self) -> None:
        """Close a failed PyPtt connection before another login attempt."""
        try:
            self.bot.connect_core.close()
        except Exception:
            # A failure can occur before PyPtt creates its socket.
            log.debug("PTT connection was already closed", exc_info=True)

    def check_status(self) -> str:
        """Return a status message about the account's registration state."""
        if self.bot.is_registered_user:
            return self._("ptt_registered", self.username)

        msg = self._("ptt_unregistered", self.username)
        if self.bot.process_picks != 0:
            msg += "\n" + self._("ptt_registration_order", self.bot.process_picks)
        return msg

    def logout(self) -> None:
        self.bot.logout()
        log.info(self._("ptt_logout_success", self.username))
