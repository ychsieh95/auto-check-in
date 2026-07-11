#!/usr/bin/env python3
"""
ApkTw client: handles login (with 2captcha-solved CAPTCHA) and session
persistence for apk.tw (Discuz! forum).
"""

import base64
import json
import logging
import pickle
import re
import requests
import time

from bs4 import BeautifulSoup
from i18n import normalize_lang, t
from pathlib import Path

log = logging.getLogger(__name__)


class ApkTw:
    """Client for logging into apk.tw, solving login CAPTCHAs via 2captcha."""

    BASE_URL = "https://apk.tw"
    LOGIN_URL = f"{BASE_URL}/member.php?mod=logging&action=login"
    LOGIN_POST_URL = (
        f"{BASE_URL}/member.php"
        "?mod=logging&action=login&loginsubmit=yes"
    )
    DEFAULT_COOKIES_FILE = Path(__file__).resolve().parent.parent / ".session_cookies.pkl"

    # CAPTCHA (seccode) handling via 2captcha
    SECCODE_MODID = "member::logging"
    TWOCAPTCHA_SUBMIT_URL = "https://2captcha.com/in.php"
    TWOCAPTCHA_RESULT_URL = "https://2captcha.com/res.php"
    TWOCAPTCHA_POLL_INTERVAL = 5   # seconds between polls
    TWOCAPTCHA_POLL_TIMEOUT = 120  # seconds before giving up on one task
    MAX_LOGIN_ATTEMPTS = 3         # retries with a fresh captcha if it's rejected

    def __init__(self, username: str, password: str, captcha_key: str | None = None,
                 cookies_file: str | Path | None = None, lang: str | None = None):
        self.username = username
        self.password = password
        self.captcha_key = captcha_key
        self.cookies_file = Path(cookies_file) if cookies_file else self.DEFAULT_COOKIES_FILE
        self.lang = normalize_lang(lang)
        self.session = self._build_session()

    @classmethod
    def from_config(cls, path: str | Path) -> "ApkTw":
        """Build a client from a JSON config file with an 'apktw' section (username/password/2captcha_key) and a top-level 'lang'."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        cfg = json.loads(config_path.read_text())
        apktw_cfg = cfg.get("apktw", {})
        missing = [k for k in ("username", "password") if not apktw_cfg.get(k)]
        if missing:
            raise ValueError(f"Config file missing required apktw key(s): {', '.join(missing)}")
        return cls(apktw_cfg["username"], apktw_cfg["password"], apktw_cfg.get("2captcha_key"), lang=cfg.get("lang"))

    def _(self, key: str, *args) -> str:
        """Translate a message key into the configured output language."""
        return t(self.lang, key, *args)

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Referer": ApkTw.BASE_URL,
        })
        return session

    def fetch_login_page(self) -> str:
        """Fetch the login page HTML (contains formhash and seccode info)."""
        log.info(self._("fetching_login_page"))
        resp = self.session.get(self.LOGIN_URL, timeout=15)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def extract_form_hash(html: str) -> str:
        """Extract the required formhash token from the login page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("input", {"name": "formhash"})
        if tag and tag.get("value"):
            return tag["value"]

        # Fallback: find formhash in raw response text
        match = re.search(r'formhash["\s]+value="([a-f0-9]+)"', html)
        if match:
            return match.group(1)

        raise RuntimeError("Could not locate formhash on login page.")

    @staticmethod
    def extract_seccode_idhash(html: str) -> str | None:
        """Extract the seccode idhash from the login page HTML, if present."""
        match = re.search(r"updateseccode\('([^']+)'", html)
        return match.group(1) if match else None

    def fetch_captcha_image(self, idhash: str) -> bytes:
        """Download the CAPTCHA image for the given seccode idhash."""
        img_url = f"{self.BASE_URL}/misc.php?mod=seccode&update={int(time.time() * 1000)}&idhash={idhash}"
        resp = self.session.get(img_url, timeout=15)
        resp.raise_for_status()
        return resp.content

    def solve_captcha(self, image_bytes: bytes) -> str:
        """Solve a CAPTCHA image via 2captcha and return the recognized text."""
        if not self.captcha_key:
            raise RuntimeError("Login requires a CAPTCHA but no 2captcha_key is configured.")

        b64 = base64.b64encode(image_bytes).decode("ascii")
        resp = requests.post(
            self.TWOCAPTCHA_SUBMIT_URL,
            data={
                "key": self.captcha_key,
                "method": "base64",
                "body": b64,
                "json": "1",
                "regsense": "1",  # case-sensitive
                "min_len": "4",
                "max_len": "4",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 1:
            raise RuntimeError(f"2captcha submit failed: {data.get('request')}")
        task_id = data["request"]

        deadline = time.monotonic() + self.TWOCAPTCHA_POLL_TIMEOUT
        while time.monotonic() < deadline:
            time.sleep(self.TWOCAPTCHA_POLL_INTERVAL)
            resp = requests.get(
                self.TWOCAPTCHA_RESULT_URL,
                params={"key": self.captcha_key, "action": "get", "id": task_id, "json": "1"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == 1:
                return data["request"]
            if data.get("request") != "CAPCHA_NOT_READY":
                raise RuntimeError(f"2captcha error: {data.get('request')}")

        raise TimeoutError(f"2captcha task {task_id} timed out after {self.TWOCAPTCHA_POLL_TIMEOUT}s")

    def login(self) -> bool:
        """Perform login and return True on success."""
        for attempt in range(1, self.MAX_LOGIN_ATTEMPTS + 1):
            html = self.fetch_login_page()
            formhash = self.extract_form_hash(html)
            log.info(self._("obtained_formhash", formhash))

            payload = {
                "formhash": formhash,
                "referer": self.BASE_URL,
                "loginfield": "username",
                "username": self.username,
                "password": self.password,
                "questionid": "0",
                "answer": "",
                "cookietime": "2592000",  # 30 days
            }

            idhash = self.extract_seccode_idhash(html)
            if idhash:
                log.info(self._("captcha_detected", idhash))
                image_bytes = self.fetch_captcha_image(idhash)
                captcha_text = self.solve_captcha(image_bytes)
                log.info(self._("captcha_solved", captcha_text))
                payload.update({
                    "seccodehash": idhash,
                    "seccodemodid": self.SECCODE_MODID,
                    "seccodeverify": captcha_text,
                })

            log.info(self._("submitting_login", self.username, attempt, self.MAX_LOGIN_ATTEMPTS))
            resp = self.session.post(self.LOGIN_POST_URL, data=payload, timeout=15)
            resp.raise_for_status()

            # Successful login redirects away from the login form
            if resp.url and "mod=logging" not in resp.url:
                log.info(self._("login_success_redirect", resp.url))
                return True

            if any(k in resp.text for k in ("欢迎您回来", "歡迎您回來", "succeedhandle_login", "main_succeed")):
                log.info(self._("login_success"))
                return True

            if idhash and "驗證碼" in resp.text:
                log.warning(self._("captcha_rejected"))
                continue

            if any(k in resp.text for k in ("密碼錯誤次數過多", "请稍后再尝试登录", "請稍後再嘗試登錄")):
                log.error(self._("login_failed_lockout"))
                return False

            if any(k in resp.text for k in ("密码错误", "密碼錯誤", "login_invalid", "errorhandle_")):
                log.error(self._("login_failed_credentials"))
                return False

            if self.session.cookies.get("auth"):
                log.info(self._("login_success_cookie"))
                return True

            log.warning(self._("login_unclear", resp.text[:400]))
            return False

        log.error(self._("login_failed_attempts", self.MAX_LOGIN_ATTEMPTS))
        return False

    def save_cookies(self) -> None:
        with open(self.cookies_file, "wb") as f:
            pickle.dump(self.session.cookies, f)
        log.info(self._("cookies_saved", self.cookies_file))

    def load_cookies(self) -> bool:
        if not self.cookies_file.exists():
            return False
        with open(self.cookies_file, "rb") as f:
            self.session.cookies.update(pickle.load(f))
        log.info(self._("cookies_loaded"))
        return True

    def verify_login(self) -> bool:
        """Check whether the current session is authenticated.

        A stale/invalidated auth cookie doesn't redirect away from
        home.php?mod=spacecp; the server just renders the same URL with a
        "please login" prompt embedded in the page, so the URL alone can't
        tell us apart from a real login. Check the page content instead.
        """
        resp = self.session.get(f"{self.BASE_URL}/home.php?mod=spacecp", timeout=15)
        if "login" in resp.url or resp.status_code != 200:
            return False
        return "action=logout" in resp.text and "您需要先登錄" not in resp.text

    def get_info(self) -> dict:
        """Fetch the current user's group and credit info.

        Returns a dict with keys: usergroup, diamond (鑽石), shard (碎鑽),
        experience (經驗), help (幫助), skill (技術), contribution (貢獻),
        promotion (宣傳), gold_beans (金豆).
        """
        info = {}

        resp = self.session.get(f"{self.BASE_URL}/home.php?mod=space&do=profile", timeout=15)
        resp.raise_for_status()
        m = re.search(r"用戶組.*?<a[^>]*ac=usergroup[^>]*>(.*?)</a>", resp.text, re.S)
        info["usergroup"] = m.group(1).strip() if m else None

        resp = self.session.get(
            f"{self.BASE_URL}/home.php?mod=spacecp&ac=credit&showcredit=1&inajax=1&ajaxtarget=extcreditmenu_menu",
            timeout=15,
        )
        resp.raise_for_status()
        text = resp.text
        credit_fields = {
            "1": "diamond",       # 鑽石
            "2": "shard",         # 碎鑽
            "3": "experience",    # 經驗
            "4": "help",          # 幫助
            "5": "skill",         # 技術
            "6": "contribution",  # 貢獻
            "7": "promotion",     # 宣傳
            "8": "gold_beans",    # 金豆
        }
        for cid, key in credit_fields.items():
            m = re.search(rf'id="hcredit_{cid}">([^<]*)</span>', text)
            info[key] = m.group(1).strip() if m else None

        log.info(self._("user_info", info))
        return info

    def checkin(self) -> dict:
        """Trigger the daily forum check-in (簽到, dsu_amupper) and return its stats.

        Loading the forum home page only shows a "my_amupper" link whose
        onclick handler fires the actual check-in via an AJAX request to
        plugin.php. If that link is present (not yet checked in today), we
        trigger it and then re-fetch the forum page to read the updated
        check-in stats.
        """
        resp = self.session.get(f"{self.BASE_URL}/forum.php", timeout=15)
        resp.raise_for_status()
        text = resp.text

        pending_m = re.search(r'id="my_amupper"[^>]*formhash=([a-f0-9]+)', text)
        if pending_m:
            log.info(self._("performing_checkin"))
            checkin_url = (
                f"{self.BASE_URL}/plugin.php?id=dsu_amupper:pper&ajax=1"
                f"&formhash={pending_m.group(1)}&zjtesttimes={int(time.time() * 1000)}"
            )
            self.session.get(checkin_url, timeout=15, headers={"X-Requested-With": "XMLHttpRequest"})

            resp = self.session.get(f"{self.BASE_URL}/forum.php", timeout=15)
            resp.raise_for_status()
            text = resp.text
        else:
            log.info(self._("already_checked_in"))

        result = {
            "total": None,
            "consecutive": None,
            "last_checkin": None,
            "checked_in_today": False,
            "message": None,
        }

        total_m = re.search(r"累計簽到[：:](?:</strong>)?\s*(\d+)\s*次", text)
        if total_m:
            result["total"] = int(total_m.group(1))

        consec_m = re.search(r"連續簽到[：:](?:</strong>)?\s*(\d+)\s*次", text)
        if consec_m:
            result["consecutive"] = int(consec_m.group(1))

        last_m = re.search(r"您上次簽到時間為</strong>:?\s*([\d\-]+\s+[\d:]+)", text)
        if last_m:
            result["last_checkin"] = last_m.group(1)

        msg_m = re.search(r'<font color="red">(.*?)</font>', text)
        if msg_m:
            result["message"] = msg_m.group(1).strip()

        # Compare dates using the server's own GMT+8 clock to avoid local
        # timezone mismatches.
        footer_m = re.search(r"GMT\+8,\s*(\d+)-(\d+)-(\d+)", text)
        if footer_m and last_m:
            today = tuple(int(p) for p in footer_m.groups())
            last_date = tuple(int(p) for p in last_m.group(1).split()[0].split("-"))
            result["checked_in_today"] = today == last_date

        if total_m or last_m:
            log.info(self._(
                "checkin_stats",
                result["total"], result["consecutive"], result["last_checkin"], result["checked_in_today"],
            ))
        else:
            log.warning(self._("checkin_not_found"))

        return result

    def ensure_logged_in(self, use_cache: bool = True) -> bool:
        """Login, reusing cached cookies if they're still valid. Returns True if authenticated."""
        if use_cache and self.load_cookies():
            log.info(self._("verifying_session"))
            if self.verify_login():
                log.info(self._("already_logged_in"))
                return True
            log.info(self._("session_expired"))

        if not self.login():
            return False

        self.save_cookies()
        return True
