from datetime import datetime

from bson import ObjectId
from odmantic import Field, Model

from src.app.common.utils.consts import MessageType


# MongoDB Collection
class Message(Model):
    id: ObjectId = Field(default_factory=ObjectId, primary_field=True)
    room_id: int
    title: str
    sender_id: int
    message_type: MessageType
    filename: str
    content: str
    user_type: str
    timestamp: datetime

    model_config = {
        "collection": "chat",
    }
