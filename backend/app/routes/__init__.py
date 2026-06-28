from fastapi import APIRouter

from app.routes import auth, board, chat, labels, static

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(board.router)
api_router.include_router(chat.router)
api_router.include_router(labels.router)

static_router = static.router
