import sqlite3
from typing import Generator, Iterable, Literal

from app.config import DEFAULT_BOARD_TITLE, INITIAL_COLUMNS, get_db_path

VALID_TABLES = {"cards", "columns"}


def connect_db() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'My Board',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS columns (
            id INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id) REFERENCES boards(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY,
            column_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0,
            due_date TEXT,
            priority TEXT DEFAULT 'none',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (column_id) REFERENCES columns(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#888888',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id) REFERENCES boards(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS card_labels (
            card_id INTEGER NOT NULL,
            label_id INTEGER NOT NULL,
            PRIMARY KEY (card_id, label_id),
            FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
        )
        """
    )
    # Add columns if they don't exist (migration for existing DBs)
    try:
        conn.execute("ALTER TABLE cards ADD COLUMN due_date TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        conn.execute("ALTER TABLE cards ADD COLUMN priority TEXT DEFAULT 'none'")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.execute("CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_columns_board_id ON columns(board_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_column_id ON cards(column_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_labels_board_id ON labels(board_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_card_labels_card_id ON card_labels(card_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_card_labels_label_id ON card_labels(label_id)")
    conn.commit()
    conn.close()


def get_or_create_user(conn: sqlite3.Connection, username: str) -> int:
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
    conn.commit()
    return int(cursor.lastrowid)


def get_or_create_board(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,)).fetchone()
    if row:
        return int(row["id"])
    cursor = conn.execute(
        "INSERT INTO boards (user_id, title) VALUES (?, ?)",
        (user_id, DEFAULT_BOARD_TITLE),
    )
    conn.commit()
    return int(cursor.lastrowid)


def ensure_seed_data(conn: sqlite3.Connection, user_id: int) -> int:
    board_id = get_or_create_board(conn, user_id)
    column_count = conn.execute(
        "SELECT COUNT(*) AS count FROM columns WHERE board_id = ?",
        (board_id,),
    ).fetchone()["count"]
    if column_count:
        return board_id

    for column_index, (column_title, cards) in enumerate(INITIAL_COLUMNS):
        column_cursor = conn.execute(
            "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
            (board_id, column_title, column_index),
        )
        column_id = int(column_cursor.lastrowid)
        for card_index, (title, details) in enumerate(cards):
            conn.execute(
                "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
                (column_id, title, details, card_index),
            )
    conn.commit()
    return board_id


def _build_board_response(
    conn: sqlite3.Connection,
    board_row: sqlite3.Row,
    board_id: int,
) -> dict:
    """Build the full board response with columns, cards, and labels."""
    column_rows = conn.execute(
        "SELECT id, title, position FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    card_rows = conn.execute(
        """
        SELECT id, column_id, title, details, position, due_date, priority
        FROM cards
        WHERE archived = 0 AND column_id IN (
            SELECT id FROM columns WHERE board_id = ?
        )
        ORDER BY column_id, position
        """,
        (board_id,),
    ).fetchall()

    label_rows = conn.execute(
        "SELECT id, name, color FROM labels WHERE board_id = ?",
        (board_id,),
    ).fetchall()
    labels_by_id = {
        str(row["id"]): {
            "id": str(row["id"]),
            "name": row["name"],
            "color": row["color"],
        }
        for row in label_rows
    }

    card_ids = [row["id"] for row in card_rows]
    card_label_rows = []
    if card_ids:
        placeholders = ",".join("?" * len(card_ids))
        card_label_rows = conn.execute(
            f"SELECT card_id, label_id FROM card_labels WHERE card_id IN ({placeholders})",
            card_ids,
        ).fetchall()

    labels_by_card: dict[int, list[str]] = {row["id"]: [] for row in card_rows}
    for row in card_label_rows:
        labels_by_card[row["card_id"]].append(str(row["label_id"]))

    cards_by_id = {
        str(row["id"]): {
            "id": str(row["id"]),
            "title": row["title"],
            "details": row["details"],
            "due_date": row["due_date"],
            "priority": row["priority"] or "none",
            "labelIds": labels_by_card.get(row["id"], []),
        }
        for row in card_rows
    }

    cards_by_column: dict[int, list[str]] = {int(row["id"]): [] for row in column_rows}
    for row in card_rows:
        cards_by_column[int(row["column_id"])].append(str(row["id"]))

    columns_payload = [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "position": row["position"],
            "cardIds": cards_by_column.get(int(row["id"]), []),
        }
        for row in column_rows
    ]

    return {
        "board": {"id": str(board_row["id"]), "title": board_row["title"]},
        "columns": columns_payload,
        "cards": cards_by_id,
        "labels": labels_by_id,
    }


def fetch_board(conn: sqlite3.Connection, user_id: int) -> dict:
    board_id = ensure_seed_data(conn, user_id)
    board_row = conn.execute(
        "SELECT id, title FROM boards WHERE id = ?",
        (board_id,),
    ).fetchone()
    return _build_board_response(conn, board_row, board_id)


def ordered_ids(rows: Iterable[sqlite3.Row]) -> list[int]:
    return [int(row["id"]) for row in rows]


def list_boards(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """List all boards for a user."""
    rows = conn.execute(
        "SELECT id, title, created_at, updated_at FROM boards WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def create_board(
    conn: sqlite3.Connection,
    user_id: int,
    title: str,
    with_default_columns: bool = True,
) -> int:
    """Create a new board for a user."""
    cursor = conn.execute(
        "INSERT INTO boards (user_id, title) VALUES (?, ?)",
        (user_id, title),
    )
    board_id = int(cursor.lastrowid)

    if with_default_columns:
        default_columns = ["Backlog", "In Progress", "Review", "Done"]
        for position, col_title in enumerate(default_columns):
            conn.execute(
                "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
                (board_id, col_title, position),
            )

    conn.commit()
    return board_id


def update_board(conn: sqlite3.Connection, board_id: int, title: str) -> None:
    """Update a board's title."""
    conn.execute(
        "UPDATE boards SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, board_id),
    )
    conn.commit()


def delete_board(conn: sqlite3.Connection, board_id: int) -> None:
    """Delete a board and all its columns/cards/labels."""
    # Get all column IDs for this board
    column_ids = conn.execute(
        "SELECT id FROM columns WHERE board_id = ?",
        (board_id,),
    ).fetchall()

    # Delete all cards in those columns (card_labels cascade)
    for row in column_ids:
        conn.execute("DELETE FROM cards WHERE column_id = ?", (row["id"],))

    # Delete all columns
    conn.execute("DELETE FROM columns WHERE board_id = ?", (board_id,))

    # Delete all labels for this board
    conn.execute("DELETE FROM labels WHERE board_id = ?", (board_id,))

    # Delete the board
    conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    conn.commit()


def get_board_owner(conn: sqlite3.Connection, board_id: int) -> int | None:
    """Get the user_id of a board's owner."""
    row = conn.execute(
        "SELECT user_id FROM boards WHERE id = ?",
        (board_id,),
    ).fetchone()
    return int(row["user_id"]) if row else None


def fetch_board_by_id(conn: sqlite3.Connection, board_id: int, user_id: int) -> dict | None:
    """Fetch a specific board by ID, verifying ownership."""
    board_row = conn.execute(
        "SELECT id, title FROM boards WHERE id = ? AND user_id = ?",
        (board_id, user_id),
    ).fetchone()
    if not board_row:
        return None
    return _build_board_response(conn, board_row, board_id)


def resequence_positions(
    conn: sqlite3.Connection,
    table: Literal["cards", "columns"],
    ids: list[int],
    extra_where: str,
    extra_params: tuple,
) -> None:
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}")
    for index, item_id in enumerate(ids):
        conn.execute(
            f"UPDATE {table} SET position = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? {extra_where}",
            (index, item_id, *extra_params),
        )


# Label management functions
def list_labels(conn: sqlite3.Connection, board_id: int) -> list[dict]:
    """List all labels for a board."""
    rows = conn.execute(
        "SELECT id, name, color FROM labels WHERE board_id = ? ORDER BY name",
        (board_id,),
    ).fetchall()
    return [
        {"id": str(row["id"]), "name": row["name"], "color": row["color"]}
        for row in rows
    ]


def create_label(conn: sqlite3.Connection, board_id: int, name: str, color: str) -> int:
    """Create a new label for a board."""
    cursor = conn.execute(
        "INSERT INTO labels (board_id, name, color) VALUES (?, ?, ?)",
        (board_id, name, color),
    )
    conn.commit()
    return int(cursor.lastrowid)


def update_label(conn: sqlite3.Connection, label_id: int, name: str | None, color: str | None) -> None:
    """Update a label's name and/or color."""
    if name is not None:
        conn.execute("UPDATE labels SET name = ? WHERE id = ?", (name, label_id))
    if color is not None:
        conn.execute("UPDATE labels SET color = ? WHERE id = ?", (color, label_id))
    conn.commit()  # single commit for both updates


def delete_label(conn: sqlite3.Connection, label_id: int) -> None:
    """Delete a label and remove it from all cards."""
    conn.execute("DELETE FROM card_labels WHERE label_id = ?", (label_id,))
    conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))
    conn.commit()


def get_label_board_id(conn: sqlite3.Connection, label_id: int) -> int | None:
    """Get the board_id for a label."""
    row = conn.execute("SELECT board_id FROM labels WHERE id = ?", (label_id,)).fetchone()
    return int(row["board_id"]) if row else None


def add_label_to_card(conn: sqlite3.Connection, card_id: int, label_id: int) -> None:
    """Add a label to a card."""
    conn.execute(
        "INSERT OR IGNORE INTO card_labels (card_id, label_id) VALUES (?, ?)",
        (card_id, label_id),
    )
    conn.commit()


def remove_label_from_card(conn: sqlite3.Connection, card_id: int, label_id: int) -> None:
    """Remove a label from a card."""
    conn.execute(
        "DELETE FROM card_labels WHERE card_id = ? AND label_id = ?",
        (card_id, label_id),
    )
    conn.commit()
