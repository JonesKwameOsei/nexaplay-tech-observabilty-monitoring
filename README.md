# NexaPlay Observability & Monitoring Stack

A production-grade observability stack built for NexaPlay Technologies — a Lagos-based online gaming company serving 180,000+ daily active players. The stack was built in response to a real incident where a server degradation went undetected for 24 minutes because the engineering team had no monitoring tools.

Everything runs locally in Docker. A single command brings up all five services.

---

## Quick Start

```bash
cp .env.example .env        # fill in your webhook URL
docker compose up -d --build
docker compose ps           # all five services should show Up
```

| Service | URL |
|---|---|
| Game server (FastAPI) | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Alertmanager | http://localhost:9093 |
| Grafana (admin / admin) | http://localhost:3000 |

> Always use `--build` on first run or after changing `app/Dockerfile` or `alertmanager/Dockerfile`. The custom images do not exist on a fresh clone until they are built.

---

## What Was Built

| Component | Description |
|---|---|
| `app/` | FastAPI game server instrumented with 4 Prometheus metrics |
| `prometheus/` | Scrape config (10s for app, 15s for everything else) + 3 alert rules |
| `alertmanager/` | Webhook routing via `envsubst` template — no secrets in version control |
| `grafana/` | 5-panel dashboard provisioned as code — no manual import needed |
| `scripts/export_to_s3.py` | Uploads dashboard JSON to S3 using a least-privilege IAM user |
| `scripts/load_generator.py` | Simulates player traffic for baseline and incident testing |
| `.github/workflows/validate.yml` | CI workflow — validates docker-compose, prometheus config, and dashboard JSON on every push |
| `runbook.md` | Response guide for all three alert rules |
| `incident-report.md` | Post-incident report from the Operation Server Meltdown simulation |

---

## Further Reading

- **[Daily journal](JOURNAL.md)** — day-by-day build log covering every decision and finding across both weeks
- **[Runbook](runbook.md)** — alert response guide for `ServiceDown`, `HighErrorRate`, and `HighMatchmakingLatency`
- **[Incident report](incident-report.md)** — full post-incident report from the Week 2 simulation

---

## Stack Architecture

```
FastAPI app ──/metrics──► Prometheus ──PromQL──► Grafana (5 panels)
                               │
                          alert rules
                               │
                               ▼
                         Alertmanager ──POST──► webhook / Slack / PagerDuty
```

Node Exporter runs alongside the app and feeds host-level metrics (CPU, memory, disk) into the same Prometheus instance.

---

## Security Notes

- `.env` is listed in `.gitignore` and has never been committed
- The S3 export IAM user has a single permission: `s3:PutObject` on one specific bucket
- No credentials appear anywhere in the repository — Alertmanager config uses `envsubst` at container startup to inject the webhook URL from the environment
