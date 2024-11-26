from fastapi import APIRouter, WebSocket


router = APIRouter(prefix="ws", tags=["Websocket"])


# Websocket
@router.websocket("/")
async def websocket(websocket: WebSocket):
    pass
