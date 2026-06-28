import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from app.database import (
    add_label_to_card,
    create_label,
    delete_label,
    get_board_owner,
    get_label_board_id,
    get_or_create_user,
    list_labels,
    remove_label_from_card,
    update_label,
)
from app.dependencies import get_authenticated_user, get_db
from app.models import CardLabelAction, LabelCreate, LabelResponse, LabelUpdate

router = APIRouter()


def _verify_board_access(conn: sqlite3.Connection, board_id: int, user_id: int) -> None:
    """Verify user has access to the board."""
    owner_id = get_board_owner(conn, board_id)
    if owner_id != user_id:
        raise HTTPException(status_code=404, detail="Board not found")


def _verify_label_access(conn: sqlite3.Connection, label_id: int, user_id: int) -> int:
    """Verify user has access to the label's board. Returns board_id."""
    board_id = get_label_board_id(conn, label_id)
    if board_id is None:
        raise HTTPException(status_code=404, detail="Label not found")
    owner_id = get_board_owner(conn, board_id)
    if owner_id != user_id:
        raise HTTPException(status_code=404, detail="Label not found")
    return board_id


@router.get("/api/boards/{board_id}/labels")
def get_labels(
    board_id: int,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[LabelResponse]:
    """Get all labels for a board."""
    user_id = get_or_create_user(conn, username)
    _verify_board_access(conn, board_id, user_id)
    labels = list_labels(conn, board_id)
    return [LabelResponse(**label) for label in labels]


@router.post("/api/boards/{board_id}/labels")
def create_board_label(
    board_id: int,
    payload: LabelCreate,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Create a new label for a board."""
    user_id = get_or_create_user(conn, username)
    _verify_board_access(conn, board_id, user_id)
    label_id = create_label(conn, board_id, payload.name, payload.color)
    return {"id": str(label_id)}


@router.patch("/api/labels/{label_id}")
def update_board_label(
    label_id: int,
    payload: LabelUpdate,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Update a label."""
    user_id = get_or_create_user(conn, username)
    _verify_label_access(conn, label_id, user_id)
    update_label(conn, label_id, payload.name, payload.color)
    return {"status": "ok"}


@router.delete("/api/labels/{label_id}")
def delete_board_label(
    label_id: int,
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Delete a label."""
    user_id = get_or_create_user(conn, username)
    _verify_label_access(conn, label_id, user_id)
    delete_label(conn, label_id)
    return {"status": "ok"}


@router.post("/api/cards/{card_id}/labels")
def add_card_label(
    card_id: int,
    payload: CardLabelAction,
    board_id: int = Query(...),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Add a label to a card."""
    user_id = get_or_create_user(conn, username)
    _verify_board_access(conn, board_id, user_id)

    # Verify card belongs to this board
    card = conn.execute(
        """
        SELECT cards.id FROM cards
        JOIN columns ON cards.column_id = columns.id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Verify label belongs to this board
    label_board_id = get_label_board_id(conn, payload.label_id)
    if label_board_id != board_id:
        raise HTTPException(status_code=404, detail="Label not found")

    add_label_to_card(conn, card_id, payload.label_id)
    return {"status": "ok"}


@router.delete("/api/cards/{card_id}/labels/{label_id}")
def remove_card_label(
    card_id: int,
    label_id: int,
    board_id: int = Query(...),
    username: str = Depends(get_authenticated_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Remove a label from a card."""
    user_id = get_or_create_user(conn, username)
    _verify_board_access(conn, board_id, user_id)

    # Verify card belongs to this board
    card = conn.execute(
        """
        SELECT cards.id FROM cards
        JOIN columns ON cards.column_id = columns.id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    remove_label_from_card(conn, card_id, label_id)
    return {"status": "ok"}
