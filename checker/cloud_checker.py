import os
import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText

# โหลด env
load_dotenv()

SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")

# เริ่มต้น Firebase
cred = credentials.Certificate(SERVICE_ACCOUNT_JSON)
firebase_admin.initialize_app(cred)
db = firestore.client()

def send_email_alert(subject, body):
    """ส่งอีเมลจาก cloud checker"""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = ALERT_EMAIL_TO

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print("ส่งอีเมลแจ้งเตือนจาก Cloud Checker แล้ว")
    except Exception as e:
        print("Error sending email:", e)

def check_last_log():
    """ตรวจสอบ log ล่าสุดใน Firestore"""
    logs = db.collection("network_logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream()
    last_log = None
    for log in logs:
        last_log = log.to_dict()

    if not last_log:
        print("ไม่มี log ในระบบ")
        return

    last_time = last_log["timestamp"]
    now = datetime.datetime.utcnow()
    diff = (now - last_time).total_seconds()

    # ถ้าเกิน 1 นาทีไม่มี log ใหม่ แสดงว่า client ไม่ได้อัปเดต (อาจเน็ตล่ม)
    if diff > 60:
        send_email_alert(
            "🚨 Client หยุดส่ง log",
            f"ตรวจพบว่าไม่มี log ใหม่ตั้งแต่ {last_time} (เกิน 1 นาที)"
        )
    else:
        print("Client ยังทำงานปกติ")

if __name__ == "__main__":
    check_last_log()
