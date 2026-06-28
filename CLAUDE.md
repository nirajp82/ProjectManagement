# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the app (Docker)
```
# Windows
scripts/start-windows.ps1

# Mac
scripts/start-mac.sh

# Linux
scripts/start-linux.sh
```
Backend and frontend are served at http://localhost:8000.

For live integration/E2E tests, start the container in detached mode first:
```
docker build -t pm-app .
docker rm -f pm-app; docker run -d --name pm-app --env-file .env -p 8000:8000 pm-app
```

### Stop the app (Docker)
```
# Windows
scripts/stop-windows.ps1

# Mac
scripts/stop-mac.sh

# Linux
scripts/stop-linux.sh
```
Or directly: `docker rm -f pm-app`

### Backend tests
```
# Unit tests (from repo root)
PYTHONPATH=. pytest backend/

# Single test file
PYTHONPATH=. pytest backend/tests/test_board_api.py

# Integration tests (needs running container)
PM_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=. pytest backend/tests/test_integration.py
```

### Frontend tests
```
cd frontend
npm run test:unit          # Vitest unit tests
npm run test:unit:watch    # Watch mode
npm run test:e2e           # Playwright E2E (needs backend on port 8000)
npm run test:all           # Unit + E2E
npm run lint               # ESLint
npm run dev                # Standalone dev server (no backend)
```

## Architecture

### System overview
Next.js 16 frontend → static export → served by FastAPI at `/`. All API routes live under `/api/*`. Everything ships in a single Docker container with SQLite for persistence.

### Authentication
JWT tokens (24h expiry, HS256) via `Authorization: Bearer`. The `get_authenticated_user` dependency in `backend/app/dependencies.py` validates tokens on every protected route. Passwords are bcrypt-hashed. `JWT_SECRET` is auto-generated per process if not set in `.env` — meaning restarts log everyone out unless `JWT_SECRET` is pinned.

### Backend layout
- `app/main.py` — FastAPI app, lifespan hook (calls `init_db()`), static file mounting
- `app/config.py` — env vars, OpenRouter settings, seed board data
- `app/database.py` — all SQL: schema init, migrations (try/except `ALTER TABLE`), every query
- `app/models.py` — Pydantic models for requests, responses, and AI action types
- `app/ai.py` — OpenRouter HTTP client, structured output parsing, action application to DB
- `app/routes/board.py` — board/column/card CRUD endpoints scoped to the signed-in user
- `app/routes/chat.py` — `/api/chat`: fetches board state, calls OpenRouter, applies actions
- `app/routes/labels.py` — label CRUD and card-label assignment

### Frontend layout
- `src/lib/api.ts` — all backend API calls; attaches JWT from `localStorage`
- `src/lib/kanban.ts` — `Card`, `Column`, `BoardData` types and pure helpers
- `src/components/KanbanBoard.tsx` — board state owner; drag-and-drop via dnd-kit; triggers refresh after AI updates
- `src/components/ChatSidebar.tsx` — AI chat UI; calls `POST /api/chat`; receives updated board in response

### AI chat flow
1. Frontend posts `{message, history}` to `POST /api/chat`
2. Backend fetches full board JSON, injects it into the system prompt
3. OpenRouter returns `{"reply": string, "actions": [...]}` — parsed in `ai.py:parse_structured_output`
4. `apply_actions()` in `ai.py` mutates SQLite (create/update/move/delete cards)
5. Backend returns the AI reply and the refreshed board in one response

AI action types: `create_card`, `update_card`, `move_card`, `delete_card`.

### Frontend ID scheme
dnd-kit requires string IDs. Frontend prefixes backend numeric IDs: columns become `"col-{id}"`, cards become `"card-{id}"`. These prefixes are stripped before any API call. Never pass prefixed IDs to the backend.

### DB migrations
No migration framework. New columns are added in `init_db()` via try/except `ALTER TABLE` blocks. The DB is auto-created at `backend/data/pm.db` (overridable via `PM_DB_PATH`).

### Environment variables (`.env` at repo root)
- `OPENROUTER_API_KEY` — required for AI features
- `JWT_SECRET` — pin this to keep sessions alive across restarts
- `PM_DB_PATH` — override SQLite path
- `PM_STATIC_DIR` — override path to built Next.js static files

### Color scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`

## Coding standards
- No over-engineering; keep it simple and direct
- No emojis anywhere
- Identify root cause before fixing; prove with evidence
- Keep README and docs minimal
