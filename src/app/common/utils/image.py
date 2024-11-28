# type: ignore
import os
from typing import List, Optional
from uuid import uuid4

import boto3
from dotenv import load_dotenv
from fastapi import HTTPException, UploadFile

load_dotenv()


class NCPStorageService:
    def __init__(
        self,
        service_name: str = "s3",
        endpoint_url: str = "https://kr.object.ncloudstorage.com",
        region_name: str = "kr-standard",
        access_key: str = os.getenv("NCP_ACCESS_KEY"),
        secret_key: str = os.getenv("NCP_SECRET_KEY"),
        bucket_name: str = os.getenv("NCP_BUCKET_NAME", "backendsam"),
    ):
        self.s3_client = boto3.client(
            service_name, endpoint_url=endpoint_url, aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region_name
        )
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url

    def _generate_unique_filename(self, original_filename: str) -> str:
        """
        고유한 파일명 생성

        :param original_filename: 원본 파일명
        :return: 고유한 파일명
        """
        ext = os.path.splitext(original_filename)[1]
        return f"{uuid4()}{ext}"

    def upload_images(self, files: List[Optional[UploadFile]]) -> List[Optional[str]]:
        """
        다중 이미지 업로드

        :param files: 업로드할 이미지 파일 리스트 (최대 3개)
        :return: 업로드된 이미지 URL 리스트
        """
        uploaded_urls = []
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]

        for file in files:
            if file is None:
                uploaded_urls.append(None)
                continue

            try:
                # 파일 확장자 검증
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in allowed_extensions:
                    uploaded_urls.append(None)
                    continue

                # 고유한 파일명 생성
                unique_filename = self._generate_unique_filename(file.filename)

                # post-image 폴더 내에 파일 저장
                object_key = f"post-image/{unique_filename}"

                # 파일 업로드
                self.s3_client.upload_fileobj(file.file, self.bucket_name, object_key, ExtraArgs={"ACL": "public-read"})

                # 업로드된 파일 URL 생성
                file_url = f"https://{self.bucket_name}.kr.object.ncloudstorage.com/{object_key}"
                uploaded_urls.append(file_url)

            except Exception as e:
                uploaded_urls.append(None)

        return uploaded_urls

    def get_s3_url(self, object_key: str) -> str:
        return f"{self.endpoint_url}/{self.bucket_name}/{object_key}"
