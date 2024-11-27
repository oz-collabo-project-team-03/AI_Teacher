from pydantic import BaseModel


class RoomCreateResponse(BaseModel):
    room_id: int
    title: str
    help_checked: bool
    participants: list[dict]
