import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import (
    create_board,
    delete_board,
    fetch_board,
    fetch_board_by_id,
    get_board_owner,
    get_or_create_board,
    get_or_create_user,
    list_boards,
    ordered_ids,
    resequence_positions,
    update_board,
)
from app.dependencies import get_authenticated_user, get_db
from app.models import (
    BoardCreate,
    BoardListResponse,
    BoardUpdate,
    CardCreate,
    CardUpdate,
    ColumnCreate,
    ColumnUpdate,
)

router = APIRouter()


# Board management endpoints
@router.get("/api/boards")
def get_boards(
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> BoardListResponse:
    """List all boards for the authenticated user."""
    user_id = get_or_create_user(conn, username)
    boards = list_boards(conn, user_id)
    return BoardListResponse(boards=boards)


@router.post("/api/boards")
def create_new_board(
    payload: BoardCreate,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Create a new board for the authenticated user."""
    user_id = get_or_create_user(conn, username)
    board_id = create_board(conn, user_id, payload.title, payload.with_default_columns)
    return {"id": str(board_id)}


@router.get("/api/boards/{board_id}")
def get_board_by_id(
    board_id: int,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Get a specific board by ID."""
    user_id = get_or_create_user(conn, username)
    board = fetch_board_by_id(conn, board_id, user_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


@router.patch("/api/boards/{board_id}")
def update_board_by_id(
    board_id: int,
    payload: BoardUpdate,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Update a board's title."""
    user_id = get_or_create_user(conn, username)
    owner_id = get_board_owner(conn, board_id)
    if owner_id != user_id:
        raise HTTPException(status_code=404, detail="Board not found")
    update_board(conn, board_id, payload.title)
    return {"status": "ok"}


@router.delete("/api/boards/{board_id}")
def delete_board_by_id(
    board_id: int,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Delete a board and all its columns/cards."""
    user_id = get_or_create_user(conn, username)
    owner_id = get_board_owner(conn, board_id)
    if owner_id != user_id:
        raise HTTPException(status_code=404, detail="Board not found")
    delete_board(conn, board_id)
    return {"status": "ok"}


# Legacy endpoint - returns the first board or creates one
@router.get("/api/board", deprecated=True)
def get_board(
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Get the default board (creates one if none exist)."""
    user_id = get_or_create_user(conn, username)
    return fetch_board(conn, user_id)


def _get_board_id_for_user(
    conn: sqlite3.Connection,
    user_id: int,
    board_id: int | None = None,
) -> int:
    """Get or validate board_id for a user."""
    if board_id is not None:
        owner_id = get_board_owner(conn, board_id)
        if owner_id != user_id:
            raise HTTPException(status_code=404, detail="Board not found")
        return board_id
    return get_or_create_board(conn, user_id)


@router.post("/api/columns")
def create_column(
    payload: ColumnCreate,
    board_id: int | None = Query(default=None),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    user_id = get_or_create_user(conn, username)
    resolved_board_id = _get_board_id_for_user(conn, user_id, board_id)

    columns = conn.execute(
        "SELECT id FROM columns WHERE board_id = ? ORDER BY position",
        (resolved_board_id,),
    ).fetchall()
    ids = ordered_ids(columns)

    insert_position = payload.position
    if insert_position is None or insert_position > len(ids):
        insert_position = len(ids)
    if insert_position < 0:
        insert_position = 0

    cursor = conn.execute(
        "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
        (resolved_board_id, payload.title, insert_position),
    )
    column_id = int(cursor.lastrowid)
    ids.insert(insert_position, column_id)
    resequence_positions(conn, "columns", ids, "AND board_id = ?", (resolved_board_id,))
    conn.commit()

    return {"id": str(column_id)}


@router.patch("/api/columns/{column_id}")
def update_column(
    column_id: int,
    payload: ColumnUpdate,
    board_id: int | None = Query(default=None),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    user_id = get_or_create_user(conn, username)
    resolved_board_id = _get_board_id_for_user(conn, user_id, board_id)

    column = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, resolved_board_id),
    ).fetchone()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    if payload.title is not None:
        conn.execute(
            "UPDATE columns SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.title, column_id),
        )

    if payload.position is not None:
        columns = conn.execute(
            "SELECT id FROM columns WHERE board_id = ? ORDER BY position",
            (resolved_board_id,),
        ).fetchall()
        ids = ordered_ids(columns)
        if column_id in ids:
            ids.remove(column_id)
        insert_position = max(0, min(payload.position, len(ids)))
        ids.insert(insert_position, column_id)
        resequence_positions(conn, "columns", ids, "AND board_id = ?", (resolved_board_id,))

    conn.commit()
    return {"status": "ok"}


@router.delete("/api/columns/{column_id}")
def delete_column(
    column_id: int,
    board_id: int | None = Query(default=None),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    user_id = get_or_create_user(conn, username)
    resolved_board_id = _get_board_id_for_user(conn, user_id, board_id)

    column = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (column_id, resolved_board_id),
    ).fetchone()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    conn.execute("DELETE FROM cards WHERE column_id = ?", (column_id,))
    conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))

    remaining = conn.execute(
        "SELECT id FROM columns WHERE board_id = ? ORDER BY position",
        (resolved_board_id,),
    ).fetchall()
    resequence_positions(conn, "columns", ordered_ids(remaining), "AND board_id = ?", (resolved_board_id,))
    conn.commit()

    return {"status": "ok"}


@router.post("/api/cards")
def create_card(
    payload: CardCreate,
    board_id: int | None = Query(default=None),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    user_id = get_or_create_user(conn, username)
    resolved_board_id = _get_board_id_for_user(conn, user_id, board_id)

    column = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?",
        (payload.column_id, resolved_board_id),
    ).fetchone()
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    cards = conn.execute(
        "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
        (payload.column_id,),
    ).fetchall()
    ids = ordered_ids(cards)

    insert_position = payload.position
    if insert_position is None or insert_position > len(ids):
        insert_position = len(ids)
    if insert_position < 0:
        insert_position = 0

    cursor = conn.execute(
        "INSERT INTO cards (column_id, title, details, position, due_date, priority) VALUES (?, ?, ?, ?, ?, ?)",
        (payload.column_id, payload.title, payload.details, insert_position, payload.due_date, payload.priority),
    )
    card_id = int(cursor.lastrowid)
    ids.insert(insert_position, card_id)
    resequence_positions(conn, "cards", ids, "AND column_id = ?", (payload.column_id,))
    conn.commit()

    return {"id": str(card_id)}


@router.patch("/api/cards/{card_id}")
def update_card(
    card_id: int,
    payload: CardUpdate,
    board_id: int | None = Query(default=None),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    user_id = get_or_create_user(conn, username)
    resolved_board_id = _get_board_id_for_user(conn, user_id, board_id)

    card = conn.execute(
        """
        SELECT cards.id, cards.column_id
        FROM cards
        JOIN columns ON cards.column_id = columns.id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, resolved_board_id),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    if payload.title is not None:
        conn.execute(
            "UPDATE cards SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.title, card_id),
        )
    if payload.details is not None:
        conn.execute(
            "UPDATE cards SET details = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.details, card_id),
        )
    if payload.due_date is not None:
        conn.execute(
            "UPDATE cards SET due_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.due_date, card_id),
        )
    if payload.priority is not None:
        conn.execute(
            "UPDATE cards SET priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.priority, card_id),
        )

    current_column_id = int(card["column_id"])
    target_column_id = payload.column_id or current_column_id

    if payload.column_id is not None:
        column = conn.execute(
            "SELECT id FROM columns WHERE id = ? AND board_id = ?",
            (payload.column_id, resolved_board_id),
        ).fetchone()
        if not column:
            raise HTTPException(status_code=404, detail="Column not found")

    if payload.position is not None or target_column_id != current_column_id:
        source_cards = conn.execute(
            "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
            (current_column_id,),
        ).fetchall()
        source_ids = ordered_ids(source_cards)
        if card_id in source_ids:
            source_ids.remove(card_id)

        target_cards = conn.execute(
            "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
            (target_column_id,),
        ).fetchall()
        target_ids = ordered_ids(target_cards)

        insert_position = payload.position
        if insert_position is None or insert_position > len(target_ids):
            insert_position = len(target_ids)
        if insert_position < 0:
            insert_position = 0

        target_ids.insert(insert_position, card_id)

        conn.execute(
            "UPDATE cards SET column_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (target_column_id, card_id),
        )
        resequence_positions(conn, "cards", source_ids, "AND column_id = ?", (current_column_id,))
        resequence_positions(conn, "cards", target_ids, "AND column_id = ?", (target_column_id,))

    conn.commit()
    return {"status": "ok"}


@router.delete("/api/cards/{card_id}")
def delete_card(
    card_id: int,
    board_id: int | None = Query(default=None),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    user_id = get_or_create_user(conn, username)
    resolved_board_id = _get_board_id_for_user(conn, user_id, board_id)

    card = conn.execute(
        """
        SELECT cards.id, cards.column_id
        FROM cards
        JOIN columns ON cards.column_id = columns.id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, resolved_board_id),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    column_id = int(card["column_id"])
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    remaining = conn.execute(
        "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
        (column_id,),
    ).fetchall()
    resequence_positions(conn, "cards", ordered_ids(remaining), "AND column_id = ?", (column_id,))
    conn.commit()
    return {"status": "ok"}
