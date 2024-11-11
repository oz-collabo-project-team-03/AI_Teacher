# Python 3.12.7 공식 이미지를 기반으로 함
FROM python:3.12.7-slim AS builder

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Poetry 설치
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

# PYTHONPATH 설정
ENV PYTHONPATH=/app/src:$PYTHONPATH

# 작업 디렉토리 설정
WORKDIR /app/src

# Poetry 설정 파일 복사
COPY pyproject.toml poetry.lock ./

# poetry.lock 파일 업데이트
RUN poetry lock --no-update

# 프로덕션 종속성만 설치
RUN poetry install --only main --no-interaction --no-ansi

# 실제 운영 이미지 생성
FROM python:3.12.7-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일만 builder 스테이지에서 복사
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY ./src /app/src

# PYTHONPATH 설정
ENV PYTHONPATH=/app:$PYTHONPATH

# 비루트 사용자 생성 및 전환
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# FastAPI 서버 실행을 위한 환경 변수 설정
ENV PORT=8000
EXPOSE 8000

# 서버 실행
CMD ["gunicorn", "src.main:app", "-w", "3", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]