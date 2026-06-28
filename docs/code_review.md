# Code Review Report

Date: 2026-06-28  
Scope: Full repository — backend, frontend, tests, config

---

## Summary

The codebase is clean and well-structured for an MVP. The architecture is intentionally simple (FastAPI + SQLite + Next.js in a single Docker container) and the code largely respects that constraint. The tests are thorough and passing. The issues below are ranked by severity.

---

## Critical

### 1. Unauthenticated requests succeed as DEFAULT_USER
**File:** `backend/app/dependencies.py:49-50`

`get_authenticated_user` falls back to `DEFAULT_USER = "user"` when no `Authorization` header and no `X-User` header are present. This means any unauthenticated HTTP request to a protected route (boards, cards, columns, labels, chat) silently succeeds and reads/writes data belonging to the `"user"` account.

```python
# Current — unauthenticated callers get free access to "user"'s data
return DEFAULT_USER
```

**Action:** Return a 401 instead of a fallback. Remove the `DEFAULT_USER` fallback from `get_authenticated_user`. The legacy `X-User` fallback can stay for now if needed, but the anonymous fallback must go.

```python
raise HTTPException(status_code=401, detail="Authentication required")
```

---

### 2. SQLite foreign key enforcement is disabled
**File:** `backend/app/database.py:9-14`

SQLite requires `PRAGMA foreign_keys = ON` per connection. `connect_db()` never sets it. All `ON DELETE CASCADE` declarations in the schema (`card_labels` referencing `cards` and `labels`) silently do nothing. The manual deletions in `delete_board` and `delete_label` paper over this today, but any future code that adds cascades will be surprised.

**Action:** Add to `connect_db()`:
```python
conn.execute("PRAGMA foreign_keys = ON")
```

---

## High

### 3. Duplicate `get_db` definition
**File:** `backend/app/database.py:114-119` and `backend/app/dependencies.py:11-16`

`get_db` is defined identically in both files. All routes import from `dependencies.py`, so the copy in `database.py` is dead code. Having two definitions creates confusion about which one is authoritative.

**Action:** Remove `get_db` from `database.py`. Keep only the one in `dependencies.py`.

---

### 4. `update_label` commits twice
**File:** `backend/app/database.py:396-403`

When both `name` and `color` are provided, `conn.commit()` is called once after each `execute`. The two updates should be committed together as one transaction.

```python
def update_label(conn, label_id, name, color):
    if name is not None:
        conn.execute("UPDATE labels SET name = ? WHERE id = ?", (name, label_id))
    if color is not None:
        conn.execute("UPDATE labels SET color = ? WHERE id = ?", (color, label_id))
    conn.commit()  # single commit
```

**Action:** Move `conn.commit()` to after both updates.

---

### 5. JWT secret too short in test/dev environments
**File:** `backend/app/config.py:16`, `backend/app/routes/auth.py:16`

`secrets.token_hex(32)` generates 64 hex characters (256 bits) — that's fine. However, the warning seen in the test suite (`InsecureKeyLengthWarning: The HMAC key is 27 bytes long`) means that some test fixture or test environment is setting a short `JWT_SECRET`. If a real deployment uses a short secret (e.g., a simple word in `.env`), tokens are easy to brute-force.

**Action:** Add a startup check that logs a warning (or refuses to start) if `JWT_SECRET` is shorter than 32 bytes. Document the minimum length in `.env.example`.

---

### 6. No rate limiting on auth endpoints
**File:** `backend/app/routes/auth.py:68-117`

`POST /api/auth/login` and `POST /api/auth/register` have no rate limiting. An attacker can attempt unlimited passwords or flood registrations.

**Action:** For the MVP Docker deployment, add a simple per-IP rate limiter using `slowapi` or document this as a known limitation that must be handled at the infrastructure level (nginx, reverse proxy) before any public exposure.

---

## Medium

### 7. Unnecessary double-ternary in card update
**File:** `backend/app/routes/board.py:304-307`

```python
if payload.due_date is not None:
    conn.execute(
        "UPDATE cards SET due_date = ? ...",
        (payload.due_date if payload.due_date else None, card_id),
    )
```

If `payload.due_date` passes the `if is not None` guard, the inner `if payload.due_date else None` is redundant — the pattern validator on the model already rejects empty strings. The inner ternary should be removed.

**Action:** Simplify to `(payload.due_date, card_id)`.

---

### 8. `AuthRequest` models defined in route file instead of `models.py`
**File:** `backend/app/routes/auth.py:20-31`

`RegisterRequest` and `LoginRequest` are Pydantic models defined inside the auth route module. All other models live in `models.py`. This is inconsistent and makes it harder to find model definitions.

**Action:** Move `RegisterRequest`, `LoginRequest`, and `AuthResponse` to `models.py`.

---

### 9. Board JSON injected verbatim into AI system prompt
**File:** `backend/app/ai.py:119`

```python
f"Current board data (JSON):\n{json.dumps(board, indent=2)}"
```

The full board JSON with `indent=2` is appended to every chat request. For a board with many cards this balloons the prompt size and increases cost and latency. The redundant `board_summary` and `column_summary` strings above it re-state the same information.

**Action:** Either remove the raw JSON (keep only the human-readable summary) or remove the human-readable summary (keep only the compact JSON without indentation). Pick one representation. If the full JSON is needed, use `json.dumps(board)` without `indent=2`.

---

### 10. Token passed as positional argument through long call chains
**File:** `frontend/src/lib/api.ts` throughout

Every exported function accepts `token?: string` as a trailing parameter (`listBoards(token?)`, `createBoard(title, withDefaultColumns, token?)`, `deleteCard(cardId, token?, boardId?)`). This is verbose and error-prone — callers must remember argument position and callers that want `boardId` but not a custom token still have to pass `token` explicitly.

**Action:** Refactor the API module to have a single factory or module-level configured `apiFetch` that reads the token from `localStorage` internally, rather than threading it through every call site. This is a larger change but eliminates an entire class of potential bugs.

---

### 11. JWT stored in `localStorage` (XSS exposure)
**File:** `frontend/src/app/page.tsx` (localStorage read/write)

Storing JWTs in `localStorage` is the standard approach for SPAs but exposes the token to any XSS. For this MVP (no user-generated HTML rendered, small attack surface) this is acceptable, but it should be a deliberate documented choice.

**Action:** Add a note to `CLAUDE.md` or `AGENTS.md` under a "Security Decisions" section documenting that `localStorage` is used for tokens and that `httpOnly` cookies are the more secure alternative for a future iteration.

---

## Low

### 12. Legacy `GET /api/board` endpoint undocumented as deprecated
**File:** `backend/app/routes/board.py:101-109`

The legacy single-board endpoint exists alongside the newer `/api/boards/*` REST endpoints with no deprecation notice.

**Action:** Add a `deprecated=True` flag to the FastAPI route decorator so it appears as deprecated in the auto-generated OpenAPI docs.

```python
@router.get("/api/board", deprecated=True)
```

---

### 13. `init_db` opens its own connection — untestable with injection
**File:** `backend/app/database.py:17`

`init_db()` calls `connect_db()` internally and closes the connection itself. This means tests cannot inject an in-memory connection for schema initialization. Current tests work because the lifespan hook creates a real file DB (which is also why there is no cross-test isolation by default).

**Action:** Add an optional `conn` parameter to `init_db` so tests can pass an in-memory connection. Existing callers pass nothing and behaviour is unchanged.

---

### 14. `get_or_create_user` creates passwordless users
**File:** `backend/app/database.py:122-128`

`get_or_create_user` inserts a user row without a `password_hash`. This is used in every route handler. If the `DEFAULT_USER` fallback (issue #1) sends an unauthenticated request, a ghost `"user"` row with no password is inserted. These users cannot log in normally.

**Action:** After fixing issue #1, `get_or_create_user` should only ever be called for authenticated users. Consider renaming it `get_user_id` and raising a 401 if the user does not exist (only the auth registration route should create users).

---

### 15. `delete_board` manually cascades instead of relying on DB cascade
**File:** `backend/app/database.py:314-334`

`delete_board` manually deletes cards, columns, then labels before deleting the board. Once `PRAGMA foreign_keys = ON` is enabled (issue #2), the schema cascades will handle cards/labels via `card_labels`. The manual deletions will become redundant but harmless. Review after fixing issue #2.

---

### 16. `test_schema.py` always skips
**File:** `backend/tests/test_schema.py`

`test_schema_json_structure` skips because the referenced schema file is absent. Either the file should be committed or the test should be removed.

**Action:** Commit the schema file or delete the test.

---

### 17. `DEP0205` deprecation warning in frontend tests
**File:** `frontend/src/test/setup.ts` (test runner output)

Every Vitest run emits `[DEP0205] DeprecationWarning: module.register() is deprecated`. This comes from a transitive dependency (likely `@vitejs/plugin-react` or a loader). While harmless now, it will become an error in a future Node.js version.

**Action:** Check if a newer version of `@vitejs/plugin-react` resolves this, or suppress the warning explicitly.

---

## Test Coverage Gaps

| Gap | Risk |
|---|---|
| No test for unauthenticated fallback to DEFAULT_USER | Masks security regression |
| No test that cross-user board access returns 404 for cards/columns | Ownership checks could regress |
| `test_chat_api.py` only tests missing API key | Full chat flow (with mocked OpenRouter) untested |
| No test for `update_label` partial update (name only, color only) | Double-commit bug in #4 undetected |
| E2E Playwright tests only run against live container | Not in Docker CI pipeline by default |

---

## Actions Checklist

| # | Severity | File | Action |
|---|---|---|---|
| 1 | Critical | `dependencies.py:50` | Remove anonymous DEFAULT_USER fallback, return 401 |
| 2 | Critical | `database.py:connect_db` | Add `PRAGMA foreign_keys = ON` |
| 3 | High | `database.py:114` | Remove duplicate `get_db` |
| 4 | High | `database.py:396` | Single `commit()` after both label updates |
| 5 | High | `config.py` | Add JWT secret length validation at startup |
| 6 | High | `routes/auth.py` | Add rate limiting on auth endpoints |
| 7 | Medium | `routes/board.py:307` | Remove redundant inner ternary on `due_date` |
| 8 | Medium | `routes/auth.py:20` | Move auth request models to `models.py` |
| 9 | Medium | `ai.py:119` | Remove duplicate board representation in system prompt |
| 10 | Medium | `api.ts` | Refactor token out of every function signature |
| 11 | Medium | `page.tsx` | Document localStorage/XSS tradeoff |
| 12 | Low | `routes/board.py:102` | Mark legacy `/api/board` as `deprecated=True` |
| 13 | Low | `database.py:17` | Make `init_db` accept optional connection |
| 14 | Low | `database.py:122` | Rename `get_or_create_user` → `get_user_id`, raise on miss |
| 15 | Low | `database.py:314` | Revisit manual cascade after fixing #2 |
| 16 | Low | `tests/test_schema.py` | Commit schema file or delete the test |
| 17 | Low | test runner | Investigate `DEP0205` deprecation in Vitest |
