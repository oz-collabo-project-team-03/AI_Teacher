import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER", "user")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD","password")

def send_email_async(recipient: str, subject: str, body: str):
    try:
        msg = MIMEText("인증코드는 000000입니다.")
        msg["From"] = SMTP_USER
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # SMTP 서버 연결 및 인증
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()  # TLS 암호화 활성화
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, recipient, msg.as_string())
        print("이메일 전송 성공!")
    except Exception as e:
        print(f"이메일 전송 실패: {e}")
