from fastapi import APIRouter, Depends, WebSocket
from odmantic import AIOEngine

from src.app.common.factory import mongo_db
from src.app.common.utils.dependency import get_current_user

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
