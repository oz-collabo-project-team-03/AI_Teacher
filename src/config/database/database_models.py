from src.app.common.models.image import Image
from src.app.common.models.tag import Tag
from src.app.v1.chat.entity.message import Message
from src.app.v1.chat.entity.participant import Participant
from src.app.v1.chat.entity.room import Room
from src.app.v1.comment.entity.comment import Comment
from src.app.v1.comment.entity.comment_tag import CommentTag
from src.app.v1.post.entity.post import Post
from src.app.v1.post.entity.post_image import PostImage
from src.app.v1.post.entity.post_like import PostLike
from src.app.v1.recomment.entity.recomment import Recomment
from src.app.v1.recomment.entity.recomment_tag import RecommentTag
from src.app.v1.user.entity.organization import Organization
from src.app.v1.user.entity.student import Student
from src.app.v1.user.entity.study_group import StudyGroup
from src.app.v1.user.entity.teacher import Teacher
from src.app.v1.user.entity.user import User

from sqlalchemy.orm import configure_mappers

# 모든 모델이 import된 후에 configure_mappers 호출
configure_mappers()
# alembic이 인식 가능하게 model import
