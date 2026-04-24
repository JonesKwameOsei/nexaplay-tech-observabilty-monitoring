# NexaPlay Monitoring Project

## The Application

A simulated NexaPlay game server built with FastAPI.
It is already instrumented with Prometheus metrics.

Available endpoints:

GET  /health              — Health check
GET  /player/login        — Simulates a player login
GET  /matchmaking/find    — Simulates matchmaking
GET  /game/session        — Simulates an active game session
GET  /metrics             — Prometheus metrics endpoint

POST /admin/incident/start  — Triggers the incident scenario
POST /admin/incident/reset  — Resets the server to normal

## Your Job

The application is already instrumented. Everything else is yours to build:

- Dockerfile and docker-compose.yml
- Prometheus configuration and alert rules
- Grafana dashboard
- Alertmanager notification routing
- AWS S3 export script
- GitHub Actions validation workflow
- Runbook and incident report

## Getting Started

1. Read the full case study document before writing a single line
2. Complete the Pre-Assessment first
3. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```
4. Start the full stack (builds custom images + starts all 5 services):
   ```bash
   docker compose up -d --build
   ```
5. Verify all containers are healthy:
   ```bash
   docker compose ps
   ```

| Service       | URL                    |
|---------------|------------------------|
| Game server   | http://localhost:8000  |
| Prometheus    | http://localhost:9090  |
| Alertmanager  | http://localhost:9093  |
| Grafana       | http://localhost:3000  |

> **Note:** Always use `--build` on first run or after changing `alertmanager/Dockerfile`
> or `app/Dockerfile`. Plain `docker compose up -d` will fail on a fresh clone
> because the custom images don't exist yet.