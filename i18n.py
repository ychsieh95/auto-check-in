#!/usr/bin/env python3
"""Minimal i18n helper for apktw output messages."""

DEFAULT_LANG = "en"

MESSAGES = {
    "en": {
        "fetching_login_page": "Fetching login page...",
        "obtained_formhash": "Obtained formhash: %s",
        "captcha_detected": "CAPTCHA detected (idhash=%s), solving via 2captcha...",
        "captcha_solved": "CAPTCHA solved as: %s",
        "submitting_login": "Submitting login form as '%s' (attempt %d/%d)...",
        "login_success_redirect": "Login succeeded (redirected to %s).",
        "login_success": "Login succeeded.",
        "captcha_rejected": "CAPTCHA was rejected, retrying with a new one...",
        "login_failed_lockout": "Login failed: too many failed attempts, account is temporarily locked out.",
        "login_failed_credentials": "Login failed: incorrect credentials or security check triggered.",
        "login_success_cookie": "Login appears to have succeeded (auth cookie present).",
        "login_unclear": "Login result unclear; response snippet:\n%s",
        "login_failed_attempts": "Login failed after %d attempts (CAPTCHA repeatedly rejected).",
        "cookies_saved": "Session cookies saved to %s",
        "cookies_loaded": "Loaded cached session cookies.",
        "user_info": "User info: %s",
        "performing_checkin": "Not checked in today yet, performing check-in...",
        "already_checked_in": "Already checked in today, skipping check-in.",
        "checkin_stats": "Check-in stats: total=%s consecutive=%s last=%s checked_in_today=%s",
        "checkin_not_found": "Could not find check-in stats on the forum page (dsu_amupper widget not found).",
        "verifying_session": "Verifying cached session...",
        "already_logged_in": "Already logged in via cached session.",
        "session_expired": "Cached session expired, re-logging in.",
        "checked_in_today": "Checked in for today. Total: %s, consecutive: %s.",
        "checkin_unclear": "Check-in status unclear: %s",
        "user_summary": "User: %s | Diamond %s | Shard %s | Experience %s | Gold beans %s",
        "done": "Done. Session is active.",
        "login_retry": "Login attempt %d/%d failed, retrying in %s seconds...",
        "login_retries_exhausted": "Login failed after %d attempt(s).",
        "telegram_error": "Error: %s",
        "apktw_header": "apk.tw Auto Check-in",
        "ptt_header": "PTT Auto Check-in",
        "ptt_login_failed": "PTT login failed: %s",
        "ptt_login_success": "Logged into PTT as '%s'.",
        "ptt_registered": "PTT account '%s' is a registered user.",
        "ptt_unregistered": "PTT account '%s' is not yet a registered user.",
        "ptt_registration_order": "Registration queue order: %s",
        "ptt_logout_success": "Logged out of PTT ('%s').",
        "no_captcha_found": "Login page did not present a CAPTCHA, skipping this attempt.",
        "captcha_saved": "Saved CAPTCHA sample %s with code '%s'.",
        "captcha_discarded": "CAPTCHA '%s' was rejected, discarding.",
        "collect_progress": "Collected %d/%d CAPTCHA samples.",
    },
    "zh-tw": {
        "fetching_login_page": "正在取得登入頁面...",
        "obtained_formhash": "已取得 formhash: %s",
        "captcha_detected": "偵測到驗證碼 (idhash=%s)，正在透過 2captcha 解析...",
        "captcha_solved": "驗證碼解析結果: %s",
        "submitting_login": "正在以 '%s' 提交登入表單（第 %d/%d 次嘗試）...",
        "login_success_redirect": "登入成功（已跳轉至 %s）。",
        "login_success": "登入成功。",
        "captcha_rejected": "驗證碼錯誤，正在重新嘗試...",
        "login_failed_lockout": "登入失敗：嘗試次數過多，帳號已被暫時鎖定。",
        "login_failed_credentials": "登入失敗：帳號密碼錯誤或觸發安全檢查。",
        "login_success_cookie": "登入似乎已成功（偵測到驗證 cookie）。",
        "login_unclear": "登入結果不明確，回應內容片段：\n%s",
        "login_failed_attempts": "經過 %d 次嘗試後登入失敗（驗證碼一直被拒絕）。",
        "cookies_saved": "Session cookies 已儲存至 %s",
        "cookies_loaded": "已載入快取的 session cookies。",
        "user_info": "使用者資訊：%s",
        "performing_checkin": "今日尚未簽到，正在執行簽到...",
        "already_checked_in": "今日已簽到，跳過簽到。",
        "checkin_stats": "簽到統計：累計=%s 連續=%s 上次=%s 今日已簽到=%s",
        "checkin_not_found": "在論壇頁面上找不到簽到資訊（找不到 dsu_amupper 區塊）。",
        "verifying_session": "正在驗證快取的 session...",
        "already_logged_in": "已透過快取的 session 登入。",
        "session_expired": "快取的 session 已過期，正在重新登入。",
        "checked_in_today": "今日簽到完成。累計：%s，連續：%s。",
        "checkin_unclear": "簽到狀態不明：%s",
        "user_summary": "使用者：%s | 鑽石 %s | 碎鑽 %s | 經驗 %s | 金豆 %s",
        "done": "完成，Session 已啟用。",
        "login_retry": "第 %d/%d 次登入嘗試失敗，將於 %s 秒後重試...",
        "login_retries_exhausted": "經過 %d 次嘗試後登入失敗。",
        "telegram_error": "錯誤：%s",
        "apktw_header": "apk.tw 自動簽到",
        "ptt_header": "PTT 自動簽到",
        "ptt_login_failed": "PTT 登入失敗：%s",
        "ptt_login_success": "已登入 PTT 帳號 '%s'。",
        "ptt_registered": "PTT 帳號 '%s' 為認證帳號。",
        "ptt_unregistered": "PTT 帳號 '%s' 尚未通過認證。",
        "ptt_registration_order": "目前排隊順位：%s",
        "ptt_logout_success": "已登出 PTT 帳號 '%s'。",
        "no_captcha_found": "登入頁面未顯示驗證碼，跳過此次嘗試。",
        "captcha_saved": "已儲存驗證碼樣本 %s，代碼為 '%s'。",
        "captcha_discarded": "驗證碼 '%s' 被拒絕，已捨棄。",
        "collect_progress": "已收集 %d/%d 個驗證碼樣本。",
    },
}


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANG
    lang = lang.strip().lower().replace("_", "-")
    return lang if lang in MESSAGES else DEFAULT_LANG


def t(lang: str | None, key: str, *args) -> str:
    """Translate `key` into `lang`, formatting with `args` if given."""
    table = MESSAGES.get(normalize_lang(lang), MESSAGES[DEFAULT_LANG])
    msg = table.get(key, MESSAGES[DEFAULT_LANG].get(key, key))
    return msg % args if args else msg
