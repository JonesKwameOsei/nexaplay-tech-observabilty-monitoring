"""
NexaPlay Load Generator
-----------------------
Simulates realistic player traffic against the NexaPlay app so that
Grafana and Prometheus have a meaningful baseline before the incident
is triggered.

Usage:
    python scripts/load_generator.py

Stop with Ctrl+C. Safe to leave running during the incident — it will
keep generating traffic so the error rate and latency panels stay active.
"""

import random
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Endpoints and their relative call weights (heavier = called more often).
# Mirrors realistic game traffic: lots of health checks and game sessions,
# frequent matchmaking, occasional logins.
ENDPOINTS = [
    ("/health",           20),
    ("/player/login",     15),
    ("/matchmaking/find", 40),
    ("/game/session",     25),
]

# Build a weighted list for random.choice
WEIGHTED_ENDPOINTS = [ep for ep, weight in ENDPOINTS for _ in range(weight)]

# How many concurrent "virtual players" to simulate
NUM_WORKERS = 5

# Seconds to pause between requests per worker (randomised per call)
MIN_DELAY = 0.3
MAX_DELAY = 1.2

# Stats counters (thread-safe via GIL for simple ints)
stats = {"total": 0, "ok": 0, "error": 0}
stats_lock = threading.Lock()


def make_request(endpoint: str) -> int:
    """Send a GET request and return the HTTP status code."""
    url = f"{BASE_URL}{endpoint}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def worker(worker_id: int):
    """Continuously send requests until the process is killed."""
    while True:
        endpoint = random.choice(WEIGHTED_ENDPOINTS)
        status = make_request(endpoint)

        with stats_lock:
            stats["total"] += 1
            if 200 <= status < 300:
                stats["ok"] += 1
            else:
                stats["error"] += 1

        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def reporter():
    """Print a one-line summary every 15 seconds."""
    while True:
        time.sleep(15)
        with stats_lock:
            total = stats["total"]
            ok    = stats["ok"]
            err   = stats["error"]
            error_pct = (err / total * 100) if total else 0.0

        ts = datetime.now().strftime("%H:%M:%S")
        print(
            f"[{ts}]  requests={total:>6}  "
            f"ok={ok:>6}  errors={err:>5}  "
            f"error_rate={error_pct:.1f}%"
        )


if __name__ == "__main__":
    print(f"Starting NexaPlay load generator — {NUM_WORKERS} workers")
    print(f"Target: {BASE_URL}")
    print("Press Ctrl+C to stop.\n")

    threads = []

    # Start worker threads
    for i in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(i,), daemon=True)
        t.start()
        threads.append(t)

    # Start reporter thread
    r = threading.Thread(target=reporter, daemon=True)
    r.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        with stats_lock:
            total = stats["total"]
            err   = stats["error"]
            error_pct = (err / total * 100) if total else 0.0
        print(f"\nStopped. Total requests: {total}  Final error rate: {error_pct:.1f}%")
