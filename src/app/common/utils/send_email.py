import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "yuhengseam@gmail.com"
SMTP_PASSWORD = "opuv zfdk lacp iawi"


def send_email(recipient: str, subject: str, body: str):
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


send_email("recipient@example.com", "테스트 이메일", "안녕하세요, 테스트 이메일입니다!")
