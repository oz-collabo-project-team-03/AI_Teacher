from datetime import datetime
from pydantic import BaseModel


class RoomCreateResponse(BaseModel):
    room_id: int
    title: str
    help_checked: bool
    student_id: int
    teacher_id: int


class RoomHelpUpdateResponse(BaseModel):
    room_id: int
    title: str
    help_checked: bool
    created_at: datetime


class RoomListResponse(BaseModel):
    room_id: int
    title: str
    help_checked: bool
    recent_message: str | None
    recent_update: str | None
    user_id: int


class RoomHelpResponse(BaseModel):
    room_id: int
    student_id: int
    student_nickname: str | None
    help_checked: bool
    recent_message: str | None
    recent_update: str | None
