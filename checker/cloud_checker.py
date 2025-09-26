import os
import json
import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText

# โหลด env (ใช้กรณีรัน local)
load_dotenv()

# ดึงค่า secrets จาก Environment
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")

# ✅ แก้ตรงนี้: แปลง SERVICE_ACCOUNT_JSON จาก string → dict
service_account_info = json.loads(SERVICE_ACCOUNT_JSON)

# เริ่มต้น Firebase ด้วย dict แทนไฟล์
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)
db = firestore.client()

def send_email_alert(subject, body):
    """ส่งอีเมลแจ้งเตือนผ่าน Gmail"""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = GMAIL_USER
        msg["To"] = ALERT_EMAIL_TO

        # ส่งอีเมลด้วย SMTP (Gmail)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print("✅ ส่งอีเมลแจ้งเตือนเรียบร้อย")
    except Exception as e:
        print("❌ Error sending email:", e)

def check_last_log():
    """ตรวจสอบ log ล่าสุดใน Firestore"""
    logs = db.collection("network_logs") \
             .order_by("timestamp", direction=firestore.Query.DESCENDING) \
             .limit(1).stream()

    last_log = None
    for log in logs:
        last_log = log.to_dict()

    if not last_log:
        print("⚠️ ไม่มี log ในระบบ")
        return

    last_time = last_log["timestamp"]
    now = datetime.datetime.utcnow()
    diff = (now - last_time).total_seconds()

    # ถ้าเกิน 1 นาทีไม่มี log ใหม่ → อาจเน็ตล่ม
    if diff > 60:
        send_email_alert(
            "🚨 Client หยุดส่ง log",
            f"ตรวจพบว่าไม่มี log ใหม่ตั้งแต่ {last_time} (เกิน 1 นาที)"
        )
    else:
        print("✅ Client ยังทำงานปกติ")

if __name__ == "__main__":
    check_last_log()
