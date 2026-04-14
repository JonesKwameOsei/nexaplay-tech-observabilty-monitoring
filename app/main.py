from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import random
import time
import threading

app = FastAPI()

# ── Metrics ───────────────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["endpoint", "status"]
)

ACTIVE_PLAYERS = Gauge(
    "nexaplay_active_players",
    "Number of currently active players"
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Request duration in seconds",
    ["endpoint"]
)

MATCHMAKING_QUEUE = Gauge(
    "nexaplay_matchmaking_queue",
    "Number of players currently in matchmaking queue"
)

# ── Incident state ────────────────────────────────────────────────────────────

incident_active = False

# ── Background: simulate active players ──────────────────────────────────────

def simulate_players():
    while True:
        if incident_active:
            ACTIVE_PLAYERS.set(random.randint(200, 400))
            MATCHMAKING_QUEUE.set(random.randint(80, 150))
        else:
            ACTIVE_PLAYERS.set(random.randint(800, 1200))
            MATCHMAKING_QUEUE.set(random.randint(10, 40))
        time.sleep(5)

threading.Thread(target=simulate_players, daemon=True).start()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    REQUEST_COUNT.labels(endpoint="/health", status="200").inc()
    return {"status": "ok"}

@app.get("/player/login")
def player_login():
    start = time.time()
    time.sleep(random.uniform(0.05, 0.15))
    REQUEST_COUNT.labels(endpoint="/player/login", status="200").inc()
    REQUEST_DURATION.labels(endpoint="/player/login").observe(time.time() - start)
    return {"message": "Player logged in"}

@app.get("/matchmaking/find")
def find_match():
    start = time.time()
    if incident_active:
        time.sleep(random.uniform(2.0, 5.0))
        if random.random() < 0.6:
            REQUEST_COUNT.labels(endpoint="/matchmaking/find", status="500").inc()
            REQUEST_DURATION.labels(endpoint="/matchmaking/find").observe(time.time() - start)
            return Response(content="Matchmaking error", status_code=500)
    else:
        time.sleep(random.uniform(0.1, 0.3))

    REQUEST_COUNT.labels(endpoint="/matchmaking/find", status="200").inc()
    REQUEST_DURATION.labels(endpoint="/matchmaking/find").observe(time.time() - start)
    return {"match_id": f"match_{random.randint(1000, 9999)}", "players": 2}

@app.get("/game/session")
def game_session():
    start = time.time()
    time.sleep(random.uniform(0.05, 0.2))
    REQUEST_COUNT.labels(endpoint="/game/session", status="200").inc()
    REQUEST_DURATION.labels(endpoint="/game/session").observe(time.time() - start)
    return {"session_id": f"session_{random.randint(1000, 9999)}", "status": "active"}

# ── Incident controls ─────────────────────────────────────────────────────────

@app.post("/admin/incident/start")
def start_incident():
    global incident_active
    incident_active = True
    return {"message": "Incident started. Matchmaking is now degraded."}

@app.post("/admin/incident/reset")
def reset_incident():
    global incident_active
    incident_active = False
    return {"message": "Incident resolved. System back to normal."}

# ── Metrics endpoint ──────────────────────────────────────────────────────────

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)