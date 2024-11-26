from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import Response

from src.app.common.utils.dependency import get_current_user
from src.app.common.utils.image import NCPStorageService  # type: ignore
from src.app.v1.post.schema.post import (
    LikeRequest,
    PostCreateRequest,
    PostUpdateRequest,
)
from src.app.v1.post.service.post import PostService

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/me")
async def get_my_posts(
    page: int = Query(default=1, gt=0),
    post_service: PostService = Depends(PostService),
    user_info: dict = Depends(get_current_user),
):
    return await post_service.get_my_posts(page=page, user_id=user_info.get("user_id"))


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


@router.put("/{post_id}")
async def post_update(
    post_id: str,
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
    update_post = PostUpdateRequest(
        content=content,
        image1=uploaded_images[0],
        image2=uploaded_images[1],
        image3=uploaded_images[2],
        is_with_teacher=is_with_teacher,
    )
    await post_service.update_post(user_id=user_info.get("user_id"), post=update_post, post_id=post_id)  # type: ignore
    return Response(status_code=status.HTTP_200_OK)


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    post_service: PostService = Depends(PostService),
    user_info: dict = Depends(get_current_user),
):
    await post_service.delete_post(user_id=user_info.get("user_id"), post_id=post_id)  # type: ignore
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{post_id}/like")
async def like_post(
    post_id: str,
    like_request: LikeRequest,
    post_service: PostService = Depends(PostService),
    user_info: dict = Depends(get_current_user),
):
    await post_service.like_post(user_id=user_info.get("user_id"), post_id=post_id, like=like_request.like)  # type: ignore

    return Response(status_code=status.HTTP_200_OK)


@router.get("")
async def get_posts(
    page: int = Query(default=1, gt=0),
    post_service: PostService = Depends(PostService),
):
    return await post_service.get_posts(page=page)
