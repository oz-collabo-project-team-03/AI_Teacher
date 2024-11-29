from fastapi import APIRouter, WebSocket, Depends
from src.app.common.utils.dependency import get_current_user
from odmantic import AIOEngine

from src.app.common.factory import mongo_db

router = APIRouter(tags=["Websocket"])


# Websocket
@router.websocket("/ws/{room_id}")
async def websocket(
    websocket: WebSocket,
    room_id: int,
    mongo: AIOEngine = Depends(mongo_db),
    current_user: dict = Depends(get_current_user),
):
    pass
