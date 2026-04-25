import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from app.config.settings import settings


class MailService:

    def send_mail_with_attachments(self, subject, body, file_paths, recipient_email=None):
        recipient = (recipient_email or settings.MAIL_TO or "").strip()
        if not recipient:
            raise ValueError("메일 수신자가 설정되지 않았습니다.")
        if not settings.MAIL_USER or not settings.MAIL_PASSWORD:
            raise ValueError("메일 발송 계정이 설정되지 않았습니다.")

        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = settings.MAIL_USER
        msg["To"] = recipient

        # 본문
        msg.attach(MIMEText(body, "plain"))

        # 🔥 여러 파일 첨부
        for file_path in file_paths:

            with open(file_path, "rb") as f:
                filename = os.path.basename(file_path)

                part = MIMEApplication(f.read(), Name=filename)
                part['Content-Disposition'] = f'attachment; filename="{filename}"'

                msg.attach(part)

        # SMTP
        smtp = smtplib.SMTP_SSL(settings.MAIL_HOST, settings.MAIL_PORT)
        smtp.login(settings.MAIL_USER, settings.MAIL_PASSWORD)
        smtp.sendmail(settings.MAIL_USER, [recipient], msg.as_string())
        smtp.quit()

        print("📧 다중 첨부 메일 발송 완료")
