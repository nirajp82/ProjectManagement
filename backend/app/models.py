from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ColumnCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    position: int | None = None


class ColumnUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    position: int | None = None


PriorityType = Literal["none", "low", "medium", "high"]


class CardCreate(BaseModel):
    column_id: int
    title: str = Field(..., min_length=1, max_length=500)
    details: str = Field(default="", max_length=5000)
    position: int | None = None
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    priority: PriorityType = "none"


class CardUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    details: str | None = Field(default=None, max_length=5000)
    column_id: int | None = None
    position: int | None = None
    due_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    priority: PriorityType | None = None


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CreateCardAction(BaseModel):
    type: Literal["create_card"]
    columnId: str
    title: str
    details: str = ""
    position: int | None = None


class UpdateCardAction(BaseModel):
    type: Literal["update_card"]
    cardId: str
    title: str | None = None
    details: str | None = None


class MoveCardAction(BaseModel):
    type: Literal["move_card"]
    cardId: str
    columnId: str
    position: int | None = None


class DeleteCardAction(BaseModel):
    type: Literal["delete_card"]
    cardId: str


ChatAction = Annotated[
    CreateCardAction | UpdateCardAction | MoveCardAction | DeleteCardAction,
    Field(discriminator="type"),
]


class StructuredChatOutput(BaseModel):
    reply: str
    actions: list[ChatAction] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] = Field(default_factory=list)
    apply_updates: bool = True


class ChatResponse(BaseModel):
    response: str
    actions: list[ChatAction] = Field(default_factory=list)
    board: dict | None = None
    model: str | None = None


# Board management models
class BoardCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    with_default_columns: bool = True


class BoardUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class BoardSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class BoardListResponse(BaseModel):
    boards: list[BoardSummary]


# Label management models
class LabelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#888888", pattern=r"^#[0-9a-fA-F]{6}$")


class LabelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class LabelResponse(BaseModel):
    id: str
    name: str
    color: str


class CardLabelAction(BaseModel):
    label_id: int


# User profile models
class UserProfile(BaseModel):
    username: str
    created_at: str


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
