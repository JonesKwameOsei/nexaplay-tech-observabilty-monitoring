# NexaPlay Observability & Monitoring Project — Daily Journal

This document contains daily accomplishments.

---

## Day 1: Setting Up Tools

**What I did today:**

Tools including `Docker Desktop, Git, VS Code, Python 3.11, AWS CLI v2` were setup. These are confirmed by running the `powershell script` below:

```ps
.\check-versions.ps1
```

**Output**:

```sh
Docker Desktop: Docker version 29.4.0
Git: git version 2.52.0.windows.1
VS Code: 
Python: Python 3.13.12
AWS CLI v2: aws-cli/2.34.20 Python/3.14.3 Windows/11 exe/AMD64
```

Also, the following files were created as part of the requirements:

- `app/Dockerfile`: builds the FastAPI app on Python 3.11-slim.
- `docker-compose.yml`: all 5 services (app, prometheus, alertmanager, node-exporter, grafana) with health checks, named volumes, and env var wiring.
- `prometheus.yml`: scrapes app, node-exporter, and itself every 15s; points to Alertmanager
- `alerts.yml`: 3 rules: ServiceDown, HighErrorRate, HighMatchmakingLatency
- `alertmanager.yml.tmpl`: routes all alerts to webhook receiver; URL pulled from .env. I am using this template file to avoid hardcoding the `Webhook url`. Hence, using a custom `Dockerfile` for `Alertmanager` that's based on `Alpine`, which includes envsubst, and uses it as the entrypoint. Here's the setup:

1. alertmanager/Dockerfile — uses Alpine-based image that copies the Alertmanager binary from the official image, installs gettext (which provides envsubst), and uses it as the entrypoint to render the template before starting alertmanager.yml.tmpl.
2. the template with ${ALERTMANAGER_WEBHOOK_URL} as a real placeholder. Alertmanager now uses build: ./alertmanager and passes ALERTMANAGER_WEBHOOK_URL from .env as an environment variable. This makes it `dynamic and production grade`. This is because the `Webhook URL` lives in .env (one place), the template is version-controlled without secrets, and any team member cloning the repo just sets their own URL in .env and runs docker compose up --build — no manual editing of config files needed.

    > Note: running `docker compose up -d` for this set up might fail. The default build command is:

    ```sh
    docker compose up --build
    ```

    ![alt text](images/docker-compose-up.png)

    ![alt text](images/docker-compose-ps.png)

- `prometheus.yml`: auto-wires Prometheus as default datasource
- `dashboard-provider.yml`: loads dashboards from the dashboards folder
- `nexaplay-overview.json`: 7 panels covering active players, matchmaking queue, request rate, error rate, response time (p50/p95), CPU, and memory

**Grafana** and **prometheus** are now accessible via localhost:3000 and localhost:9090 respectively.

![grafana-login](images/grafana-login.png)
![grafana-ui](images/grafana-ui.png)

![alt text](images/prometehus-ui.png)

AWS CLI configured, confirmed by running:

```sh
aws sts get-caller-identity
```

**Output**:

```sh
{
    "UserId": "MyUserID",
    "Account": "xxxxxxxxxxxxxxx",
    "Arn": "arn:aws:iam::xxxxxxxxxxxxxxx:user/myuser"
}
```

---

## Day 2: Setup Prometheus & Metrics

### Metrics defined in `app/main.py`

#### 1. `http_requests_total`

- **Type:** Counter
- **Labels:** `endpoint`, `status`
- **Measures:** The total number of HTTP requests received. Incremented on every route handler call via `.inc()`. Broken down by endpoint path (e.g. `/health`, `/player/login`) and HTTP status code (e.g. `200`, `500`). Because it's a Counter it only ever goes up, making it ideal for tracking cumulative request volume and deriving request rates with `rate()`.

#### 2. `nexaplay_active_players`

- **Type:** Gauge
- **Measures:** The number of players currently active on the platform. Set every 5 seconds by a background thread via `.set()`. During normal operation it fluctuates between 800–1200; during an incident it drops to 200–400, making it a direct signal of platform health.

#### 3. `http_request_duration_seconds`

- **Type:** Histogram
- **Labels:** `endpoint`
- **Measures:** How long each request takes to complete, in seconds. Recorded via `.observe(elapsed)` at the end of each route handler. As a Histogram it buckets observations automatically, enabling percentile queries (p50, p95, etc.) in Prometheus with `histogram_quantile()`.

#### 4. `nexaplay_matchmaking_queue`

- **Type:** Gauge
- **Measures:** The number of players currently waiting in the matchmaking queue. Also set every 5 seconds by the same background thread. Normal range is 10–40; during an incident it spikes to 80–150. A rising queue depth is an early warning sign of matchmaking degradation before errors start appearing.

### Access Prometheus UI and Run PromQL

Prometheus is accessible via `localhost:9090`. 

![prometheus-ui](images/prometehus-ui.png)

To be certain that Prometheus can reach all the scrape targets, the foolowing queries are run:

```promql
up
```

![up](images/prometehus-instances-up.png)

This single most important query returns  1 (healthy) or 0 (down) for every target. 

Froom the image all the three targets are reached, hence, 1 is returned for all the targets. The targets can also be reached on `http://localhost:9090/targets`.

To check the the total requests the app has handled, we run:

```promql
http_requests_total
```

![total_requests](images/prometheus-total_requests.png)

```promql
rate(http_requests_total[2m]) * 100
```

![rate_of_requests](images/request-rate-per-second.png)

This shows throughput broken down by endpoint and status labels. Baseline for understanding normal traffic patterns before an incident happens.

Next, the number of players currently connected or playiing on the app can be determined:

```promql
nexaplay_active_players
```

![active_players](images/nexa_active_players.png)

Over thouusand active players are currently playing. Is this number affecting memory usage? A query could answer this question:

```promql
process_resident_memory_bytes
```

![memory_usage_bytes](images/memory-usage-bytes.png)

This returns the memory usage in bytes which can be hard to read. To make it more readable, we convert it to megabyte by dividing it by 1o24^2 (1024 / 1024):

```promql
process_resident_memory_bytes / 1024^2
```

![memory_usage_by_megabytes](images/memory-usage-mb.png)

### Update Prometheus Scrape Interval

The cuurent configuration for the `scrape_interval`for the app target is `15s`. I will update it to `10s`. But before, let's confirm the current intervals:

**Get all scrape_intervals**:
  
```sh
curl -s http://localhost:9090/api/v1/status/config | jq -r '.data.yaml' | grep 'scrape_interval'
```

**Output**:

```sh
scrape_interval: 15s
scrape_interval: 15s
scrape_interval: 15s
scrape_interval: 15s
```

**Get scrape_intervals for only `nexaplay-app`**:
  
```sh
curl -s http://localhost:9090/api/v1/status/config | jq -r '.data.yaml' | yq '.scrape_configs[] | select(.job_name == "nexaplay-app") | .scrape_interval'
```

**Output**:

```sh
15s
```

We will `validate` before reloading:

```sh
promtool check config /path/to/prometheus.yml     # run if prometheus is locally installed.

                 or

docker exec -it nexaplay-prometheus promtool check config //etc//prometheus//prometheus.yml    # if running it on docker (use single / if running on unix system)
```

**Output**:

```sh
^[[FChecking //etc//prometheus//prometheus.yml
  SUCCESS: 1 rule files found
 SUCCESS: //etc//prometheus//prometheus.yml is valid prometheus config file syntax

Checking /etc/prometheus/rules/alerts.yml
  SUCCESS: 3 rules found
```

**Reload prometheus after modifying the scrape_interval to 10s for the app** by running:

```sh
curl -X POST localhost:9090/-/reload
```

**Reconfirm scrape interval for for all and app only**:

```sh
curl -s http://localhost:9090/api/v1/status/config | jq -r '.data.yaml' | grep 'scrape_interval'
```

**Output**:

```sh
scrape_interval: 15s
scrape_interval: 10s
scrape_interval: 15s
scrape_interval: 15s
```

```sh
curl -s http://localhost:9090/api/v1/status/config | jq -r '.data.yaml' | yq '.scrape_configs[] | select(.job_name == "nexaplay-app") | .scrape_interval'
```

**Output**:

```sh
10s
```

This is evident that the 10s scrape_interval for the app has been successfully configured. Verification from UI:

![prometheus_targets](images/prometheus-target.png)

---
