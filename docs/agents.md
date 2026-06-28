# Docker Build and Run Guide

## Prerequisites

- Docker Desktop installed and running
- `.env` file at the repo root (see `.env` section below)

## Required `.env` file

Create `.env` in the repo root:

```env
OPENROUTER_API_KEY=sk-or-v1-...       # Required for AI chat features
JWT_SECRET=your-long-random-secret    # Pin this to keep sessions alive across restarts
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct:free  # Optional; overridable per-request from the UI
```

If `JWT_SECRET` is omitted, a random secret is generated each run and all sessions are invalidated on restart.

## Build the Docker image

Run from the repo root:

```powershell
docker build -t pm-app .
```

The build compiles the Next.js frontend (Node 20) and installs the Python backend dependencies. Expect 2-4 minutes on first build; subsequent builds use layer cache.

## Run the container

```powershell
# Detached (background) — recommended
docker rm -f pm-app
docker run -d --name pm-app --env-file .env -p 8000:8000 pm-app

# Foreground (see live logs) — terminal stays attached; Ctrl+C to stop
docker rm -f pm-app
docker run --name pm-app --env-file .env -p 8000:8000 pm-app
```

App is available at http://localhost:8000.

## View logs

```powershell
docker logs pm-app          # Last N lines
docker logs -f pm-app       # Follow (stream)
```

## Stop and remove

```powershell
docker rm -f pm-app
```

## Rebuild after code changes

Any change to backend Python or frontend TypeScript/TSX requires a full image rebuild:

```powershell
docker build -t pm-app .
docker rm -f pm-app
docker run -d --name pm-app --env-file .env -p 8000:8000 pm-app
```

## Default account

On first startup the backend seeds a default user automatically:

| Field    | Value      |
|----------|------------|
| Username | `user`     |
| Password | `password` |

This account includes a pre-populated board with sample cards in each column. Seeding is idempotent — restarting the container does not reset data if the SQLite database file persists (it lives inside the container at `/app/backend/data/pm.db`; to persist across container recreations, mount a volume).

## AI model selection

The ChatSidebar includes a model dropdown with free OpenRouter models. Users can also type any model ID via the "Other" option. The selection is saved in `localStorage`. To change the server-side default, update `OPENROUTER_MODEL` in `.env` and rebuild.

Free models that work well for structured chat output:

| Model ID | Notes |
|----------|-------|
| `meta-llama/llama-3.1-8b-instruct:free` | Default; reliable JSON output |
| `meta-llama/llama-3.2-3b-instruct:free` | Smaller, faster |
| `google/gemma-2-9b-it:free` | Google; strong instruction following |
| `mistralai/mistral-7b-instruct:free` | Mistral baseline |
| `qwen/qwen-2.5-7b-instruct:free` | Qwen; good at structured tasks |
| `deepseek/deepseek-r1:free` | DeepSeek reasoning model |

Use the "Other" option in the sidebar to try any model available at https://openrouter.ai/models.

## Health check

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Expected response: `{ "status": "ok" }`
