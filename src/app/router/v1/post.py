from fastapi import APIRouter, Depends
from starlette import status
from starlette.responses import Response

from src.app.v1.post.schema.post import PostCreateRequest
from src.app.v1.post.service.post import PostService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/write")
async def post_write(post: PostCreateRequest, post_service: PostService = Depends(PostService)):
    user_id = "some_user_id"

    return await post_service.create_post(user_id=user_id, post=post)
