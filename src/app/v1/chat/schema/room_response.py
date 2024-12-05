from datetime import datetime
from pydantic import BaseModel, ConfigDict
from src.app.v1.chat.entity.room import Room
from src.app.v1.chat.entity.message import Message
from src.app.common.utils.consts import MessageType


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


class PaginationResponse(BaseModel):
    current_page: int
    total_pages: int
    total_messages: int


class RoomMessageResponse(BaseModel):
    sender_id: int
    content: str
    timestamp: str
    message_type: MessageType
    user_type: str


class RoomMessagesListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    room_id: int
    title: str
    help_checked: bool
    ai_profile: str
    student_profile: str | None
    teacher_profile: str | None
    student_nickname: str | None
    teacher_nickname: str | None
    messages: list[RoomMessageResponse]
    pagination: PaginationResponse

    @classmethod
    def from_room_and_messages(
        cls,
        room: Room,
        messages: list[Message],
        ai_profile: str,
        student_profile: str,
        teacher_profile: str,
        student_nickname: str,
        teacher_nickname: str,
        page: int,
        total_pages: int,
        total_messages: int,
    ) -> "RoomMessagesListResponse":
        return cls(
            room_id=room.id,
            title=room.title,
            help_checked=room.help_checked,
            ai_profile=ai_profile,
            student_profile=student_profile,
            teacher_profile=teacher_profile,
            student_nickname=student_nickname,
            teacher_nickname=teacher_nickname,
            messages=[
                RoomMessageResponse(
                    sender_id=msg.sender_id, content=msg.content, timestamp=msg.timestamp, message_type=msg.message_type, user_type=msg.user_type
                )
                for msg in messages
            ],
            pagination=PaginationResponse(current_page=page, total_pages=total_pages, total_messages=total_messages),
        )


class StudentInfo(BaseModel):
    room_id: int | None = None
    student_id: int
    student_nickname: str
    student_image_url: str
    help_checked: bool


class TeacherInfo(BaseModel):
    teacher_id: int
    teacher_image_url: str
    teacher_nickname: str


class TeacherStudentsResponse(BaseModel):
    teacher: TeacherInfo
    students: list[StudentInfo]


class RoomHelpResponse(BaseModel):
    room_id: int
    student_id: int
    student_nickname: str | None
    help_checked: bool
    recent_message: str | None
    recent_update: str | None
