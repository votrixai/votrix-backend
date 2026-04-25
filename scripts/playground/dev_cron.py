"""
Local dev cron simulator.

Calls POST /internal/cron/tick every 60 seconds, mimicking Cloud Scheduler.
Run in a second terminal alongside uvicorn:

    python scripts/dev_cron.py
"""

import time
import urllib.request

URL = "http://localhost:8000/internal/cron/tick"
INTERVAL = 60


def tick():
    req = urllib.request.Request(URL, method="POST", data=b"")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"[cron] tick → {resp.status} {resp.read().decode()}")
    except Exception as exc:
        print(f"[cron] tick failed: {exc}")


if __name__ == "__main__":
    print(f"[cron] dev simulator started, firing every {INTERVAL}s → {URL}")
    while True:
        tick()
        time.sleep(INTERVAL)
