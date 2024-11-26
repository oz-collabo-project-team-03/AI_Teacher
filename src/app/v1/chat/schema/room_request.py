from pydantic import BaseModel


class RoomCreateRequest(BaseModel):
    title: str
