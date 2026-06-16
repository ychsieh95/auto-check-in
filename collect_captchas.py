#!/usr/bin/env python3
"""
Collect a labeled apk.tw CAPTCHA dataset.

Repeatedly fetches a fresh login CAPTCHA, solves it via 2captcha, and submits
a login attempt using the configured username/password. Whenever the CAPTCHA
is accepted (not rejected by the server), the image is saved to
`captchas/<n>.png` and its solved code is appended to `captchas/labels.csv`.

Usage: python collect_captchas.py --config config.json --count 20
"""

import argparse
import csv
import logging
import time

from apktw.apktw import ApkTw
from i18n import normalize_lang, t
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

def _next_index(captchas_dir: Path) -> int:
    existing = [int(p.stem) for p in captchas_dir.glob("*.png") if p.stem.isdigit()]
    return max(existing, default=-1) + 1


def _save_sample(captcha_dir: Path, label_dir: Path, image_bytes: bytes, code: str) -> Path:
    captcha_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)
    labels_file = label_dir / "labels.csv"
    is_new = not labels_file.exists()
    image_path = captcha_dir / f"{_next_index(captcha_dir)}.png"
    image_path.write_bytes(image_bytes)
    with open(labels_file, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["filename", "code"])
        writer.writerow([image_path.name, code])
    return image_path


def collect_one(client: ApkTw, captcha_dir: Path, label_dir: Path) -> str | None:
    """Attempt one login with a fresh CAPTCHA.

    If the CAPTCHA is accepted, save it as a labeled sample and return the
    solved code; otherwise return None.
    """
    html = client.fetch_login_page()
    formhash = client.extract_form_hash(html)
    idhash = client.extract_seccode_idhash(html)
    if not idhash:
        log.warning(client._("no_captcha_found"))
        return None

    image_bytes = client.fetch_captcha_image(idhash)
    captcha_text = client.solve_captcha(image_bytes)

    payload = {
        "formhash": formhash,
        "referer": ApkTw.BASE_URL,
        "loginfield": "username",
        "username": client.username,
        "password": client.password,
        "questionid": "0",
        "answer": "",
        "cookietime": "0",
        "seccodehash": idhash,
        "seccodemodid": ApkTw.SECCODE_MODID,
        "seccodeverify": captcha_text,
    }
    resp = client.session.post(ApkTw.LOGIN_POST_URL, data=payload, timeout=15)
    resp.raise_for_status()

    if "驗證碼" in resp.text:
        log.info(client._("captcha_discarded", captcha_text))
        return None

    path = _save_sample(captcha_dir, label_dir, image_bytes, captcha_text)
    log.info(client._("captcha_saved", path.name, captcha_text))
    return captcha_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a labeled apk.tw CAPTCHA dataset")
    parser.add_argument("--config", default="config.json", metavar="CONFIG_FILE", help="JSON config file (default: config.json)")
    parser.add_argument("--count", type=int, default=20, help="Number of accepted CAPTCHA samples to collect (default: 20)")
    parser.add_argument("--delay", type=float, default=5, help="Seconds to wait between login attempts (default: 5)")
    parser.add_argument("--captcha-output-dir", default="./captchas", metavar="DIR", help="Directory to save CAPTCHA images into (default: ./captchas)")
    parser.add_argument("--label-output-dir", default="./captchas", metavar="DIR", help="Directory to save labels.csv into (default: ./captchas)")
    parser.add_argument("--lang", default=None, help="Output language (en, zh-tw); overrides config")
    args = parser.parse_args()

    base = ApkTw.from_config(args.config)
    lang = normalize_lang(args.lang) if args.lang else base.lang
    captcha_dir = Path(args.captcha_output_dir)
    label_dir = Path(args.label_output_dir)

    collected = 0
    while collected < args.count:
        client = ApkTw(base.username, base.password, base.captcha_key, lang=lang)
        try:
            if collect_one(client, captcha_dir, label_dir):
                collected += 1
        except Exception:
            log.exception("Failed to collect a CAPTCHA sample")
        log.info(t(lang, "collect_progress", collected, args.count))
        if collected < args.count:
            time.sleep(args.delay)


if __name__ == "__main__":
    main()
