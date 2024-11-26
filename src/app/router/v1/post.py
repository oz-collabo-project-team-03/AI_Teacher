from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import Response

from src.app.common.utils.dependency import get_current_user
from src.app.common.utils.image import NCPStorageService  # type: ignore
from src.app.v1.post.schema.post import PostCreateRequest
from src.app.v1.post.service.post import PostService

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post("/write")
async def post_write(
    content: str = Form(...),
    image1: Optional[UploadFile] = File(None),
    image2: Optional[UploadFile] = File(None),
    image3: Optional[UploadFile] = File(None),
    is_with_teacher: bool = Form(False),
    post_service: PostService = Depends(PostService),
    ncp_storage_service: NCPStorageService = Depends(NCPStorageService),
    user_info: dict = Depends(get_current_user),
):
    uploaded_images = ncp_storage_service.upload_images([image1, image2, image3])

    post = PostCreateRequest(
        content=content,
        image1=uploaded_images[0],
        image2=uploaded_images[1],
        image3=uploaded_images[2],
        is_with_teacher=is_with_teacher,
    )

    await post_service.create_post(user_id=user_info.get("user_id"), post=post)  # type: ignore

    return Response(status_code=status.HTTP_201_CREATED)


@router.get("/{post_id}")
async def post_get(post_id: str, post_service: PostService = Depends(PostService)):
    return await post_service.get_post(post_id)
