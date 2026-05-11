# NexaPlay Runbook

This runbook is for anyone responding to an alert from the NexaPlay observability stack. You do not need to have seen the system before — each entry tells you what the alert means, what to check first, the common causes, and how to resolve it.

The stack runs as five Docker containers: `nexaplay-app`, `nexaplay-prometheus`, `nexaplay-alertmanager`, `nexaplay-node-exporter`, `nexaplay-grafana`. All commands assume you are in the project root directory.

---

## Alert: `ServiceDown`

**Severity:** Critical
**Rule:** `up{job="nexaplay-app"} == 0` for 1 minute
**What it means:** Prometheus has been unable to scrape the NexaPlay game server for more than 1 minute. The app container is either crashed, stopped, or unreachable on the network. Players cannot connect and active sessions may be dropping.

---

### What to check first

**1. Is the container running?**

```sh
docker compose ps
```

Look at the `app` row. `Status` should say `Up` or `Up (healthy)`. If it says `Exited`, `Restarting`, or is missing, the container has stopped or is crash-looping.

**2. What do the logs say?**

```sh
docker compose logs --tail=50 app
```

Look for Python tracebacks, `OOMKilled`, or port-binding errors. This tells you whether the crash was a code error, a resource problem, or a config issue.

**3. Is Prometheus itself healthy?**

Open `http://localhost:9090/targets`. The `nexaplay-app` row should show `UP`. If Prometheus is down, the alert may be a false positive from the monitoring layer, not the app.

---

### Common causes

| Symptom in logs | Cause | Fix |
|---|---|---|
| `Address already in use` | Port 8000 is held by another process | `docker compose down` then `docker compose up -d` |
| `ModuleNotFoundError` | Python dependency missing from image | `docker compose up --build` to rebuild |
| `OOMKilled` | Container exceeded memory limit | Check Memory panel in Grafana; increase Docker memory limit |
| Container missing from `docker compose ps` | Container was manually stopped or never started | `docker compose start app` |
| Repeated `Restarting` with no log output | Crash on startup before logging initialises | `docker compose logs app` immediately after start to catch early output |

---

### How to resolve

**Simple restart (container stopped, logs show clean exit):**

```sh
docker compose start app
```

Wait 30 seconds, then confirm recovery (see below).

**Rebuild restart (dependency or config change):**

```sh
docker compose up --build -d app
```

**Full stack restart (unsure of cause):**

```sh
docker compose down
docker compose up -d
```

Rebuilds all images and starts every service fresh. Takes 60–90 seconds.

---

### How to confirm recovery

- `http://localhost:9090/targets` — `nexaplay-app` shows **UP**
- `http://localhost:9090/alerts` — `ServiceDown` shows **inactive**
- Grafana dashboard — Active Players panel returns to green (800–1200 range)
- Alertmanager sends a `status: "resolved"` notification to the webhook

---

## Alert: `HighErrorRate`

**Severity:** Warning
**Rule:** `rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m]) * 100 > 5` for 2 minutes
**What it means:** More than 5% of HTTP requests have been returning 5xx (server error) responses for at least 2 consecutive minutes. The app is running but returning errors to players. Matchmaking, login, or game sessions may be failing.

---

### What to check first

**1. Which endpoint is failing?**

Open the Grafana dashboard and look at the **Request Rate (per second)** time series panel. A `/matchmaking/find 500` or `/player/login 500` series appearing in the legend tells you exactly which endpoint is affected.

**2. Is incident mode active?**

The app has a built-in incident simulation mode. Check its status:

```sh
curl http://localhost:8000/health
```

If the app responds, it is running. Then check whether the errors are coming from the simulation:

```sh
docker compose logs --tail=50 app
```

Look for repeated 500 responses on `/matchmaking/find`.

**3. What does the Error Rate panel show?**

Open Grafana. The **Error Rate (%)** stat panel shows the current percentage. If it reads 100%, every matchmaking request is failing — this is total endpoint failure, not a partial degradation.

---

### Common causes

| Observation | Cause | Fix |
|---|---|---|
| Error rate exactly 60% on `/matchmaking/find` | Incident simulation mode is active (`incident_active = True` in app) | `curl -X POST http://localhost:8000/admin/incident/reset` |
| Error rate climbing gradually after a deploy | Code regression introduced in a recent change | Roll back the image: `docker compose up --build -d` with the previous code |
| Error rate spikes then recovers repeatedly | Intermittent dependency failure (e.g. downstream service timing out) | Check logs for timeout errors; consider adding retries |
| Error rate high but CPU and memory normal | Application-level logic error, not a resource problem | Read logs for the specific exception being thrown |
| Error rate high AND memory climbing | Possible memory leak causing request failures under pressure | Check Memory panel trend; restart app and monitor |

---

### How to resolve

**If incident simulation mode is the cause:**

```sh
curl -X POST http://localhost:8000/admin/incident/reset
```

Wait ~60 seconds for the Prometheus `rate()` window to roll past the last 500 responses. The Error Rate panel will return to "No data".

**If the cause is a code or config error:**

```sh
docker compose restart app
```

If the error persists after restart, the issue is in the code or config, not transient state. Read the logs carefully before restarting again.

**If you cannot identify the cause:**

```sh
docker compose logs --tail=200 app > /tmp/app-errors.txt
```

Save the logs before restarting so you have evidence for the post-incident review.

---

### How to confirm recovery

- Grafana **Error Rate (%)** panel returns to "No data" (no 5xx series in the scrape window)
- Grafana **Request Rate** panel shows only 200-status series; all 500 series disappear from the legend
- Grafana **Active Players** panel returns to green (800–1200 range)
- `http://localhost:9090/alerts` — `HighErrorRate` shows **inactive**
- Alertmanager sends a `status: "resolved"` notification to the webhook

---

## Alert: `HighMatchmakingLatency`

**Severity:** Warning
**Rule:** `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/matchmaking/find"}[2m])) > 1.0` for 1 minute
**What it means:** The 95th percentile response time for `/matchmaking/find` has exceeded 1 second for at least 1 minute. Matchmaking is slow — 1 in 20 players is waiting more than 1 second to find a game. This was the exact failure mode in the Eid al-Fitr 2024 incident.

---

### What to check first

**1. Is the overall request rate unusually high?**

Check the **Request Rate** panel in Grafana. A sudden traffic surge (e.g. tournament start) can slow matchmaking without any code change.

**2. Is incident mode active?**

Incident mode artificially inflates matchmaking response time to 2–5 seconds:

```sh
curl -X POST http://localhost:8000/admin/incident/reset
```

If latency drops immediately after this, incident mode was the cause.

**3. Is CPU elevated?**

Check the **CPU Usage** gauge in Grafana. If CPU is above 80%, the host is under load and all endpoints will be slow.

---

### Common causes

| Observation | Cause | Fix |
|---|---|---|
| Latency high, incident mode active | Simulation is running | `curl -X POST http://localhost:8000/admin/incident/reset` |
| Latency high, CPU > 80% | Host resource exhaustion | Reduce load or scale the service |
| Latency high, CPU normal, error rate normal | Slow dependency (e.g. database full table scan) | Profile the matchmaking handler; check for missing indexes |
| Latency high only at tournament start times | Traffic spike exceeding single-instance capacity | Pre-scale before known high-traffic events |

---

### How to resolve

**If incident simulation mode is the cause:**

```sh
curl -X POST http://localhost:8000/admin/incident/reset
```

**If it is a genuine load issue:**

```sh
docker compose restart app
```

This clears any in-memory queue backlog. Monitor the **Request Rate** panel to confirm throughput returns to normal.

---

### How to confirm recovery

- Grafana **Request Rate** panel — `/matchmaking/find` response times return to the 100–300 ms baseline
- `http://localhost:9090/alerts` — `HighMatchmakingLatency` shows **inactive**
- Alertmanager sends a `status: "resolved"` notification to the webhook

---

*Last updated: Week 2, Day 4*
