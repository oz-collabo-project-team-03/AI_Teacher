from pydantic import BaseModel


class PostCreateRequest(BaseModel):
    content: str
    image1: str
    image2: str
    image3: str
