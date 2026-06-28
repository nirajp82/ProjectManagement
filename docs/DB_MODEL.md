# Database model (proposal)

This proposal is for the MVP and targets SQLite.

## Goals
- Support multiple users in the database.
- Enforce one board per user for the MVP.
- Keep ordering stable for columns and cards.

## Tables

### users
- Stores account records (future-ready).
- `username` is unique.

### boards
- One board per user (unique `user_id`).
- Title stored for future multi-board expansion.

### columns
- Ordered by `position` within a board.
- Renaming columns updates the `title`.

### cards
- Linked to columns, ordered by `position` within a column.
- `details` is a required text field (empty string allowed).
- `archived` is a soft-delete flag for future use.

## Ordering strategy
- `position` is an integer, starting at 0 and incremented by 1.
- Reordering updates affected `position` values within the parent scope.

## Migration approach
- Use SQLite DDL migrations tracked by version.
- Store version in `PRAGMA user_version` and increment on migration.
- Keep migrations idempotent and forward-only.

## JSON schema reference
- See docs/kanban-schema.json
