import os
from pathlib import Path

from app.ai import apply_actions, parse_structured_output
from app.database import connect_db, fetch_board, get_or_create_user, init_db
from app.models import CreateCardAction, DeleteCardAction, MoveCardAction, UpdateCardAction


def test_parse_structured_output() -> None:
    import json
    content = json.dumps(
        {
            "reply": "All set.",
            "actions": [
                {
                    "type": "create_card",
                    "columnId": "1",
                    "title": "New card",
                    "details": "Details",
                    "position": 0,
                }
            ],
        }
    )

    parsed = parse_structured_output(content)
    assert parsed.reply == "All set."
    assert parsed.actions
    assert parsed.actions[0].type == "create_card"


def test_apply_actions_updates_board(tmp_path: Path) -> None:
    os.environ["PM_DB_PATH"] = str(tmp_path / "test.db")
    init_db()

    conn = connect_db()
    user_id = get_or_create_user(conn, "user")
    board = fetch_board(conn, user_id)

    first_column = board["columns"][0]
    second_column = board["columns"][1]
    first_card_id = board["columns"][0]["cardIds"][0]

    actions = [
        CreateCardAction(
            type="create_card",
            columnId=first_column["id"],
            title="AI card",
            details="",
            position=0,
        ),
        MoveCardAction(
            type="move_card",
            cardId=first_card_id,
            columnId=second_column["id"],
            position=0,
        ),
        UpdateCardAction(
            type="update_card",
            cardId=first_card_id,
            title="Updated title",
        ),
        DeleteCardAction(
            type="delete_card",
            cardId=first_card_id,
        ),
    ]

    apply_actions(conn, user_id, actions)
    updated = fetch_board(conn, user_id)

    assert any(card["title"] == "AI card" for card in updated["cards"].values())
    assert first_card_id not in updated["cards"]
    conn.close()
