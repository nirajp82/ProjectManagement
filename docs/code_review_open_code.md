# Code Review Report (opencode)

Date: 2026-06-28
Scope: Full repository -- backend, frontend, tests, config
Reviewer: opencode

---

## Summary

Well-structured MVP with clean architecture (FastAPI + SQLite + Next.js in single Docker container). The existing `docs/code_review.md` already documents 17 issues; many have since been fixed. This review covers remaining issues and new findings.

**Issues resolved since prior review:**
- Anonymous `DEFAULT_USER` fallback removed (now returns 401)
- `PRAGMA foreign_keys = ON` enabled in `connect_db()`
- Duplicate `get_db` removed from `database.py`
- `update_label` now uses single `commit()`
- JWT secret length check added at startup
- Auth request models moved to `models.py`
- Board JSON removed from AI system prompt (uses summary only)
- Legacy `/api/board` marked `deprecated=True`
- `kanban-schema.json` committed, `test_schema.py` no longer skips
- Redundant inner ternary on `due_date` removed

---

## Medium

### 1. `get_or_create_user` creates passwordless users in every route handler

**Files:** `backend/app/routes/board.py:39,51,63,78,93,108,133,168,207,237,279,367` and `backend/app/routes/labels.py:47,61,75,88,103,136`

Every protected route calls `get_or_create_user(conn, username)` which inserts a user row without `password_hash` if the user doesn't exist. If the JWT references a deleted user, this silently creates a ghost user that cannot log in normally.

**Action:** Replace `get_or_create_user` with `get_user_id` that raises 404 if not found. Only `POST /api/auth/register` should create users.

---

### 2. `scripts/AGENTS.md` is stale

**File:** `scripts/AGENTS.md:1`

Says "This folder will contain start and stop scripts for Mac, PC and Linux" but all 6 scripts already exist.

**Action:** Update to accurately describe the folder contents.

---

### 3. No `.env.example` file

`.env` is in `.gitignore` but there is no `.env.example` template for new developers. The OpenRouter API key setup flow is undocumented for first-time setup.

**Action:** Create `.env.example` at repo root with commented-out placeholder values for `OPENROUTER_API_KEY`, `JWT_SECRET`, and `OPENROUTER_MODEL`.

---

### 4. `test_main.py` uses module-level `TestClient` and mutates module state

**File:** `backend/tests/test_main.py:9`

`client = TestClient(app)` is module-level. Tests monkey-patch `static_module.STATIC_DIR` (e.g., lines 35, 50, 62, 70, 104, 113). If tests ever run in parallel or share state, this will cause flaky failures.

**Action:** Use a fixture for `TestClient` and restore `STATIC_DIR` in a `finally` block or use `mock.patch.object`.

---

### 5. `test-results/.last-run.json` committed

**File:** `frontend/test-results/.last-run.json`

Playwright artifacts directory is not in `.gitignore`. Generated files should not be tracked.

**Action:** Add `test-results/` to `.gitignore` and remove tracked files.

---

### 6. `page.tsx` is too large (735 lines)

**File:** `frontend/src/app/page.tsx`

Handles auth state, board loading, drag-and-drop persistence, chat with retry logic, error handling, login/register forms, and loading states. Exceeds single-responsibility principle.

**Action:** Extract into custom hooks: `useAuth()`, `useBoard()`, `useChat()`. Extract login/register form into a shared component.

---

### 7. BoardSelector delete confirmation uses browser `confirm()`

**File:** `frontend/src/components/BoardSelector.tsx:95`

`confirm("Delete ...")` blocks the event loop and cannot be styled. For MVP this is acceptable, but it breaks keyboard accessibility and custom modal patterns.

**Action:** Replace with a controlled modal or inline confirmation UI.

---

### 8. CSS background decorations duplicated across `page.tsx`

**File:** `frontend/src/app/page.tsx:489-490, 501-503, 665-666`

The same two `radial-gradient` background divs appear in 3 branches (loading, unauthenticated, loading/error).

**Action:** Extract into a shared `BackgroundDecoration` component.

---

### 9. `KanbanBoard` creates cards with hardcoded details string

**File:** `frontend/src/components/KanbanBoard.tsx:166`

Fallback card creation sets `details: "No details yet."` when `onAddCard` callback is not provided. The backend allows empty string details. Inconsistent behavior.

**Action:** Use empty string `""` to match backend behavior, or remove the fallback branch entirely.

---

## Low

### 10. Docker pip install uv version is unpinned

**File:** `Dockerfile:22`

`pip install --no-cache-dir uv` installs whatever version is latest. The standard uv Dockerfile pattern uses a pinned version.

**Action:** Pin uv version for reproducible builds, e.g., `pip install uv==0.5.x`.

---

### 11. Playwright webServer config is heavy for CI

**File:** `frontend/playwright.config.ts:22`

The `webServer` command runs the start script which does `docker build + docker run`. This requires Docker and adds 2-4 minutes per test run. The `reuseExistingServer: true` pattern helps but the build always runs.

**Action:** Split CI into separate build and test stages. Let Playwright assume a running container from an earlier CI step.

---

### 12. Integration test skip functions evaluated at module load time

**File:** `backend/tests/test_integration.py:9-14`

`_can_run()` and `_can_run_openrouter()` are module-level functions. `@pytest.mark.skipif` evaluates them at import time, not test time. If env vars change during test collection, skip decisions are stale.

**Action:** Use a fixture-based skip or evaluate at test time with `pytest.skip()` inside the test body.

---

### 13. `KanbanBoard` aliases `onBoardChange` to `setBoard`

**File:** `frontend/src/components/KanbanBoard.tsx:57`

`const setBoard = onBoardChange;` is a trivial alias that adds indirection without benefit.

**Action:** Use `onBoardChange` directly or rename the prop to `setBoard`.

---

## Test Coverage Gaps

| Gap | Risk |
|---|---|
| No test for registration -> login -> board creation flow | Core user journey untested |
| `test_ai_actions.py` does not test `parse_structured_output` with malformed JSON | Error handling could regress |
| No test verifying cross-user isolation (user A cannot see user B's board) | Security regression possible |
| No frontend tests for `BoardSelector` dropdown open/close/delete | UI behavior could break |
| Backend unit tests in `test_main.py` do not isolate DB per test | Tests share filesystem state |
| No test for `formatDueDate` edge cases (null, invalid, boundary dates) | Date display could regress |

---

## Things done well

- Clean, consistent code formatting throughout both backend and frontend
- Good use of FastAPI dependency injection for DB connection lifecycle
- Frontend/backend ID prefix scheme (`col-`, `card-`) with `ensure_prefix` guards against double-prefixing
- Chat retry logic with 429 rate-limit handling spans frontend UI + backend response
- CSS variables match the specified color scheme exactly, used consistently across all components
- Tests are pragmatic -- not chasing coverage metrics but testing meaningful behaviors
- DB migration approach via try/except `ALTER TABLE` is simple and appropriate for MVP
- `TestClient` auth header helper pattern in board tests is clean and reusable
