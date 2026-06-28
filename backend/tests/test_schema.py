import json
from pathlib import Path

import pytest


def test_schema_json_structure() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "docs" / "kanban-schema.json"
    if not schema_path.exists():
        pytest.skip("Schema file not available in this environment")
    data = json.loads(schema_path.read_text())

    assert data["db"] == "sqlite"
    assert data["schemaVersion"]

    tables = {table["name"]: table for table in data["tables"]}
    assert {"users", "boards", "columns", "cards"}.issubset(tables.keys())

    users_columns = {col["name"] for col in tables["users"]["columns"]}
    assert {"id", "username", "created_at"}.issubset(users_columns)

    boards_columns = {col["name"] for col in tables["boards"]["columns"]}
    assert {"id", "user_id", "title"}.issubset(boards_columns)

    columns_columns = {col["name"] for col in tables["columns"]["columns"]}
    assert {"id", "board_id", "title", "position"}.issubset(columns_columns)

    cards_columns = {col["name"] for col in tables["cards"]["columns"]}
    assert {"id", "column_id", "title", "details", "position"}.issubset(cards_columns)
