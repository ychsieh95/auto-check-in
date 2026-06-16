#!/usr/bin/env python3
"""
Telegram sender: sends messages via the Telegram Bot API using the
bot token and chat id from config.json.
"""

import json
import logging
import requests

from pathlib import Path

log = logging.getLogger(__name__)


class TelegramSender:
    """Sends messages to a Telegram chat via the Bot API."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @classmethod
    def from_config(cls, path: str | Path) -> "TelegramSender":
        """Build a sender from a JSON config file with a 'notify.telegram' section (bot_token/chat_id)."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        cfg = json.loads(config_path.read_text())
        telegram_cfg = cfg.get("notify", {}).get("telegram", {})
        missing = [k for k in ("bot_token", "chat_id") if not telegram_cfg.get(k)]
        if missing:
            raise ValueError(f"Config file missing required notify.telegram key(s): {', '.join(missing)}")
        return cls(telegram_cfg["bot_token"], telegram_cfg["chat_id"])

    def send(self, message: str, parse_mode: str | None = None) -> bool:
        """Send a text message to the configured chat. Returns True on success."""
        url = self.API_URL.format(token=self.bot_token)
        payload = {"chat_id": self.chat_id, "text": message}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            resp = requests.post(url, data=payload, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            log.error("Failed to send Telegram message: %s", exc)
            return False

        if not resp.json().get("ok"):
            log.error("Telegram API returned an error: %s", resp.text)
            return False
        return True
