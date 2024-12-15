from pydantic import BaseModel


class MessageResponse(BaseModel):
    room_id: int
    title: str
    sender_id: int
    content: str
    message_type: str
    user_type: str
    timestamp: str
