# auto-check-in

Automated daily check-in for [apk.tw](https://apk.tw) (a Discuz! forum) and
[PTT](https://www.ptt.cc/) (批踢踢實業坊), with Telegram status notifications.

For apk.tw, this logs in (solving the login CAPTCHA via
[2captcha](https://2captcha.com)), performs the daily check-in, and reports
your account stats. For PTT, it logs in and reports your registration status.

## Files

- `apktw/apktw.py` — `ApkTw` client class: login (with CAPTCHA solving),
  session caching, daily check-in, and account info.
- `ptt/ptt.py` — `PttCheckin` client class: PTT login and registration status.
- `utils/telegram_sender.py` — `TelegramSender` class for posting status
  notifications to a Telegram chat.
- `main.py` — CLI entry point that ties it all together.
- `collect_captchas.py` — collects a labeled apk.tw CAPTCHA dataset.
- `i18n.py` — output message translations (`en`, `zh-tw`).
- `config.example.json` — example config file.
- `requirements.txt` — Python dependencies.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Copy the example config and fill in your credentials:

```bash
cp config.example.json config.json
```

```json
{
  "apktw": {
    "username": "your_username",
    "password": "your_password",
    "2captcha_key": "your_2captcha_api_key"
  },
  "ptt": {
    "username": "your_ptt_username",
    "password": "your_ptt_password"
  },
  "notify": {
    "telegram": {
      "bot_token": "your_telegram_bot_token",
      "chat_id": "your_telegram_chat_id"
    }
  },
  "lang": "zh-tw"
}
```

- `apktw.2captcha_key` — API key from [2captcha.com](https://2captcha.com),
  used to solve the login CAPTCHA.
- `notify.telegram` — optional; if present, a status summary is sent to this
  Telegram chat via the bot after each run.
- `lang` — output language, `"en"` or `"zh-tw"` (optional, defaults to `en`).

## Usage

```bash
python3 main.py --config config.json --type all
```

This will:

1. **apk.tw**: reuse a cached session (`.session_cookies.pkl`) if it's still
   valid, otherwise log in (solving the CAPTCHA via 2captcha). Perform the
   daily check-in and report the streak/total plus account info
   (usergroup, 鑽石/碎鑽/經驗/金豆, etc).
2. **PTT**: log in and report whether the account is a registered user (and
   its registration queue position if not).
3. Send a summary of both runs via the channel(s) given in `--notify`
   (currently `telegram`), if the matching `notify.*` section is configured.

Login failures are retried automatically based on `--login-retries` (default
3 times).

### Options

| Flag | Description |
| --- | --- |
| `--config CONFIG_FILE` | JSON config file (default: `config.json`) |
| `--type` | Which check-in(s) to run: `apktw`, `ptt`, `all` (default: `all`); accepts multiple values |
| `--lang` | Output language, `en` or `zh-tw`; overrides config |
| `--no-cache` | (apk.tw) Ignore cached cookies and force a fresh login |
| `--login-retries` | Number of times to retry if login fails (default: 3) |
| `--retry-delay` | Seconds to wait between login retries (default: 10) |
| `--notify` | Send a notification summary after running via the given channel(s): `telegram` (requires matching `notify.*` config); accepts multiple values |

To run only one service:

```bash
python3 main.py --config config.json --type apktw
python3 main.py --config config.json --type ptt
```

### Scheduling

Run it once a day with cron, e.g.:

```cron
0 8 * * * cd /path/to/auto-check-in && .venv/bin/python main.py --config config.json --notify telegram
```

### Collecting a CAPTCHA dataset

```bash
python3 collect_captchas.py --config config.json --count 20
```

For each attempt, this fetches a fresh login CAPTCHA, solves it via 2captcha,
and submits a login using the configured `apktw` username/password. Whenever
the CAPTCHA is accepted, the image is saved to `captchas/<n>.png` and its
solved code is appended to `captchas/labels.csv` (`filename,code`). Rejected
CAPTCHAs are discarded. Use `--delay` to control the wait between attempts
(default: 5s) and `--output-dir` to change where samples are saved (default:
`./captchas`).

## Notes

- `config.json` and `.session_cookies.pkl` contain credentials/session data
  and are gitignored — never commit them.
- The `captchas/` directory holds a labeled CAPTCHA image dataset used while
  developing the 2captcha integration; it's not required at runtime.
