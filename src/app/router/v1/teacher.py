from fastapi import APIRouter


router = APIRouter(prefix="/teahcer", tags=["Teachers"])


# 관리 학생 목록 조회
@router.get("/students", response_model="")
async def get_students():
    pass


# 헬프 목록 조회
@router.get("helps", response_model="")
async def get_help_list():
    pass
