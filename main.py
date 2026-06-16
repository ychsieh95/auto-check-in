#!/usr/bin/env python3
"""
Unified auto check-in entry point.
Usage: python main.py --config config.json --type apktw ptt
       python main.py --config config.json --type all
"""

import argparse
import logging
import time

from apktw.apktw import ApkTw
from i18n import normalize_lang, t
from ptt.ptt import PttCheckin
from utils.telegram_sender import TelegramSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def run_apktw(config: str, lang: str | None, login_retries: int, retry_delay: float, no_cache: bool) -> str:
    """Run the apk.tw check-in and return a status message for notification."""
    client = ApkTw.from_config(config)
    if lang:
        client.lang = normalize_lang(lang)

    logged_in = False
    for attempt in range(1, login_retries + 1):
        if client.ensure_logged_in(use_cache=not no_cache):
            logged_in = True
            break
        if attempt < login_retries:
            log.warning(t(client.lang, "login_retry", attempt, login_retries, retry_delay))
            time.sleep(retry_delay)

    if not logged_in:
        msg = t(client.lang, "login_retries_exhausted", login_retries)
        log.error(msg)
        return f"{t(client.lang, 'apktw_header')}\n{msg}"

    try:
        stats = client.checkin()
        if stats["checked_in_today"]:
            checkin_msg = t(client.lang, "checked_in_today", stats["total"], stats["consecutive"])
            log.info(checkin_msg)
        else:
            checkin_msg = t(client.lang, "checkin_unclear", stats)
            log.warning(checkin_msg)

        info = client.get_info()
        summary_msg = t(
            client.lang, "user_summary",
            info["usergroup"], info["diamond"], info["shard"], info["experience"], info["gold_beans"],
        )
        log.info(summary_msg)
    except Exception as exc:
        log.exception("apk.tw check-in failed")
        return f"{t(client.lang, 'apktw_header')}\n{t(client.lang, 'telegram_error', exc)}"

    log.info(t(client.lang, "done"))
    return f"{t(client.lang, 'apktw_header')}\n{checkin_msg}\n{summary_msg}"


def run_ptt(config: str, lang: str | None, login_retries: int, retry_delay: float) -> str:
    """Run the PTT check-in and return a status message for notification."""
    client = PttCheckin.from_config(config)
    if lang:
        client.lang = normalize_lang(lang)

    try:
        logged_in = False
        for attempt in range(1, login_retries + 1):
            if client.login():
                logged_in = True
                break
            if attempt < login_retries:
                log.warning(t(client.lang, "login_retry", attempt, login_retries, retry_delay))
                time.sleep(retry_delay)

        if not logged_in:
            msg = t(client.lang, "login_retries_exhausted", login_retries)
            log.error(msg)
            return f"{t(client.lang, 'ptt_header')}\n{msg}"

        status_msg = client.check_status()
        log.info(status_msg)
        client.logout()
    except Exception as exc:
        log.exception("PTT check-in failed")
        return f"{t(client.lang, 'ptt_header')}\n{t(client.lang, 'telegram_error', exc)}"

    return f"{t(client.lang, 'ptt_header')}\n{status_msg}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified auto check-in (apk.tw / PTT)")
    parser.add_argument("--config", default="config.json", metavar="CONFIG_FILE", help="JSON config file (default: config.json)")
    parser.add_argument(
        "--type", nargs="+", choices=["apktw", "ptt", "all"], default=["all"],
        help="Which check-in(s) to run (default: all)",
    )
    parser.add_argument("--lang", default=None, help="Output language (en, zh-tw); overrides config")
    parser.add_argument("--no-cache", action="store_true", help="(apktw) Ignore cached cookies and force re-login")
    parser.add_argument("--login-retries", type=int, default=3, help="Number of times to retry if login fails (default: 3)")
    parser.add_argument("--retry-delay", type=float, default=10, help="Seconds to wait between login retries (default: 10)")
    parser.add_argument(
        "--notify", nargs="+", choices=["telegram"], default=[],
        help="Send a notification summary after running via the given channel(s) (requires matching config under 'notify')",
    )
    args = parser.parse_args()

    types = set(args.type)
    if "all" in types:
        types = {"apktw", "ptt"}

    telegram = None
    if "telegram" in args.notify:
        try:
            telegram = TelegramSender.from_config(args.config)
        except (FileNotFoundError, ValueError):
            telegram = None

    messages = []
    if "apktw" in types:
        messages.append(run_apktw(args.config, args.lang, args.login_retries, args.retry_delay, args.no_cache))
    if "ptt" in types:
        messages.append(run_ptt(args.config, args.lang, args.login_retries, args.retry_delay))

    if telegram:
        telegram.send("\n\n".join(messages))


if __name__ == "__main__":
    main()
