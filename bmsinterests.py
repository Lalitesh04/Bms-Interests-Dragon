#!/usr/bin/env python3

import os
import re
import json
import time
import random
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

# =================================================
# CONFIG
# =================================================
IST = timezone(timedelta(hours=5, minutes=30))

BMS_URL = "https://in.bookmyshow.com/movies/bengaluru/ntr-31/ET00311251"
MOVIE_CODE = "ET00311251"

BASE_FOLDER = "data"
EVENT_FILE = os.path.join(BASE_FOLDER, f"{MOVIE_CODE}.json")

os.makedirs(BASE_FOLDER, exist_ok=True)

# =================================================
# HELPERS
# =================================================
def ist_now_iso():
    return datetime.now(IST).isoformat(timespec="minutes")


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def parse_interested(value: str) -> int:

    value = value.replace(",", "").strip().upper()

    if value.endswith("K"):
        return int(float(value[:-1]) * 1000)

    return int(re.findall(r"\d+", value)[0])


def get_last_interest(history: dict):
    if not history:
        return None
    last_ts = max(history.keys())
    return history[last_ts]

# =================================================
# SCRAPER
# =================================================
def scrape_bms_interest():
    time.sleep(random.uniform(1.0, 2.5))

    scraper = cloudscraper.create_scraper(
        browser={
            "browser": "chrome",
            "platform": "windows",
            "mobile": False
        }
    )

    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": "https://in.bookmyshow.com/",
    }

    res = scraper.get(BMS_URL, headers=headers, timeout=15)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    for el in soup.find_all(
        ["div", "span", "section", "p", "h1", "h2", "h3", "h4"]
    ):
        text = el.get_text(" ", strip=True).lower()

        if "interested" in text:
            m = re.search(r"(\d+(\.\d+)?)\s*k", text, re.I)
            if m:
                return m.group(1).upper() + "K"

            m = re.search(r"\b\d{4,}\b", text)
            if m:
                return m.group(0)

    return None

# =================================================
# MAIN
# =================================================
def run():
    timestamp = ist_now_iso()

    try:
        raw = scrape_bms_interest()
        if not raw:
            print("[WARN] Interested count not found")
            return

        interested = parse_interested(raw)

        # -------- LOAD / INIT FILE --------
        data = load_json(EVENT_FILE, {
            "eventCode": MOVIE_CODE,
            "source": "BookMyShow",
            "timezone": "Asia/Kolkata",
            "last_updated": None,
            "history": {}
        })

        history = data.get("history", {})

        # 🔒 Rule 1: Skip if interest unchanged
        last_value = get_last_interest(history)
        if last_value is not None and interested == last_value:
            print(
                f"[SKIP] {MOVIE_CODE} | Interest unchanged ({interested})"
            )
            return

        # 🔒 Rule 2: Do not overwrite same timestamp
        if timestamp in history:
            print(
                f"[SKIP] {MOVIE_CODE} | Timestamp already exists {timestamp}"
            )
            return

        # ✅ SAVE CHANGE
        history[timestamp] = interested
        data["history"] = history
        data["last_updated"] = timestamp

        save_json(EVENT_FILE, data)

        print(
            f"[OK] {MOVIE_CODE} | Interested: {interested} | IST {timestamp}"
        )

    except Exception as e:
        print("[ERROR] SCRAPE_FAILED:", str(e))


if __name__ == "__main__":
    run()
