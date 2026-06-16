#!/usr/bin/env python3
"""
PttCheckin client: handles login and registration-status reporting for
PTT (批踢踢實業坊) via PyPtt.
"""

import json
import logging

from i18n import normalize_lang, t
from pathlib import Path
from PyPtt import PTT

log = logging.getLogger(__name__)


class PttCheckin:
    """Client for logging into PTT and reporting account status."""

    def __init__(self, username: str, password: str, lang: str | None = None):
        self.username = username
        self.password = password
        self.lang = normalize_lang(lang)
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

    def login(self) -> bool:
        """Log into PTT. Returns True on success."""
        try:
            self.bot.login(self.username, self.password)
        except Exception as exc:
            log.warning(self._("ptt_login_failed", exc))
            return False
        log.info(self._("ptt_login_success", self.username))
        return True

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
