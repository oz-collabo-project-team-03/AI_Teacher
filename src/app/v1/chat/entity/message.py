from bson import ObjectId
from odmantic import Model, Field
from src.app.common.utils.consts import MessageType


# MongoDB Collection
class Message(Model):
    id: ObjectId = Field(default_factory=ObjectId, primary_field=True)
    room_id: int
    title: str
    sender_id: int
    message_type: MessageType
    content: str
    user_type: str
    timestamp: str

    model_config = {
        "collection": "chat",
    }
