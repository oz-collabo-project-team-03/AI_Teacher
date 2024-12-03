from openai import OpenAI
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# OpenAI API 키 설정 (여기에 API 키 입력)

# OpenAI API 키 설정
client = OpenAI(api_key=OPENAI_API_KEY)  # API 키 입력

# 대화 기록 저장 (문맥 유지)
messages = [
    {"role": "system", "content": "너는 수행평가를 돕는 친절한 AI 선생님이야."},
]

print("=== 수행평가 AI 채팅 ===")
print("종료하려면 'exit'를 입력하세요.")

while True:
    # 사용자 입력
    user_input = input("사용자: ")
    if user_input.lower() == "exit":
        print("채팅을 종료합니다.")
        break

    # 대화 기록에 사용자 메시지 추가
    messages.append({"role": "user", "content": user_input})

    try:
        # OpenAI API 호출
        completion = client.chat.completions.create(
            model="gpt-4-turbo",  # 모델 선택
            messages=messages,  # type: ignore 대화 기록 전달
            stream=True,  # 스트리밍 활성화
        )

        # 스트리밍 응답 처리
        print("AI: ", end="")
        for chunk in completion:
            chunk_content = chunk.choices[0].delta.content
            if isinstance(chunk_content, str):
                print(chunk_content, end="")
        print()  # 응답 끝에 줄바꿈 추가

    except Exception as e:
        print(f"오류 발생: {e}")