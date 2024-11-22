import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Argon2 -> 비밀번호 해쉬화
ph = PasswordHasher()


def validate_password_complexity(password: str) -> bool:
    return bool(re.match(r"^(?=.*[a-zA-Z])(?=.*\d)[A-Za-z\d]{10,20}$", password))


def hash_password(password: str) -> str:
    try:
        return ph.hash(password)
    except Exception as e:
        raise ValueError("비밀번호 해싱 중 오류가 발생했습니다.")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, password)
    except VerifyMismatchError:
        return False
