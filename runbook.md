# NexaPlay Runbook

This runbook is written for anyone who needs to respond to an alert from the NexaPlay observability stack — even if you have never seen the system before. Each entry covers what the alert means, what to check first, and how to fix it.

---

## Alert: `ServiceDown`

**Severity:** Critical

### What this alert means

Prometheus has been unable to reach the NexaPlay game server for more than 1 minute. The server is either crashed, stopped, or unreachable on the network. While this alert is firing, players cannot connect and active sessions may be dropping.

### What to check first

1. **Is the container running?**

   Open a terminal and run:

   ```sh
   docker compose ps
   ```

   Look at the `app` row. The `Status` column should say `Up`. If it says `Exited` or is missing entirely, the container has stopped.

2. **What caused it to stop?**

   Check the last few lines of the container logs:

   ```sh
   docker compose logs --tail=50 app
   ```

   Look for Python tracebacks, `OOMKilled` (out of memory), or port-binding errors. This tells you whether the crash was a code error, a resource problem, or a configuration issue.

3. **Is Prometheus itself healthy?**

   Open `http://localhost:9090/targets` in a browser. The `nexaplay-app` row should show `UP`. If Prometheus itself is down, the alert may be a false positive caused by the monitoring layer, not the app.

### How to restore the service

**If the container is stopped and the logs show a clean exit or a recoverable error:**

```sh
docker compose start app
```

Wait about 30 seconds, then check `http://localhost:9090/targets` to confirm the target is back to `UP`. The `ServiceDown` alert will move to **inactive** in the Prometheus UI and Alertmanager will send a `resolved` notification to the webhook.

**If the container keeps crashing (restart loop):**

```sh
docker compose logs --tail=100 app
```

Read the error. Common causes:

| Symptom in logs | Fix |
|---|---|
| `Address already in use` | Another process is using port 8000. Run `docker compose down` then `docker compose up -d`. |
| `ModuleNotFoundError` | A Python dependency is missing. Run `docker compose up --build` to rebuild the image. |
| `OOMKilled` | The container ran out of memory. Check the memory panel in Grafana and consider increasing Docker's memory limit. |

**If you are unsure what caused the crash**, do a full clean restart:

```sh
docker compose down
docker compose up --build -d
```

This rebuilds all images and starts every service fresh. It takes about 60–90 seconds. Once up, verify all five services are healthy:

```sh
docker compose ps
```

All rows should show `Up` or `Up (healthy)`.

### How to confirm recovery

- `http://localhost:9090/alerts` — `ServiceDown` should show **inactive**
- `http://localhost:9090/targets` — `nexaplay-app` should show **UP**
- `http://localhost:3000` — the Grafana dashboard should show active players rising back toward the 800–1200 normal range

---

## Alert: `HighErrorRate`

**Severity:** Warning

### What this alert means

More than 5% of HTTP requests to the NexaPlay app have been returning 5xx (server error) responses for at least 2 consecutive minutes. Players are hitting errors.

### What to check first

Check the app logs for Python exceptions:

```sh
docker compose logs --tail=100 app
```

Also check whether incident mode is active (this is a built-in simulation feature):

```sh
curl http://localhost:8000/admin/incident/status
```

### How to restore the service

If incident mode is on, stop it:

```sh
curl -X POST http://localhost:8000/admin/incident/stop
```

If the errors are real, check the logs for the root cause and restart the app if needed:

```sh
docker compose restart app
```

---

## Alert: `HighMatchmakingLatency`

**Severity:** Warning

### What this alert means

The 95th percentile response time for the `/matchmaking/find` endpoint has exceeded 1 second for at least 1 minute. Matchmaking is slow — players are waiting longer than normal to find a game.

### What to check first

- Check the Request Rate panel in Grafana for a traffic spike.
- Check the Active Players panel — a sudden surge in players can overload matchmaking.
- Check CPU usage on the Grafana dashboard.

### How to restore the service

If the latency is caused by incident mode:

```sh
curl -X POST http://localhost:8000/admin/incident/stop
```

If it is a genuine load issue, consider restarting the app to clear any in-memory queue backlog:

```sh
docker compose restart app
```

---

*Last updated: Week 2, Day 1*
