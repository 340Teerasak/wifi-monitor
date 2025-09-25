import os
import time
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ping3
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# โหลด environment variables จากไฟล์ .env
load_dotenv()

# กำหนดค่าต่าง ๆ จาก env (ต้องตั้งก่อนใช้งานจริง)
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")  # ไฟล์ json ของ Firebase service account
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO")

# ตัวแปรกันสแปม: แจ้งเตือน 1 ครั้งต่อ 5 นาที
LAST_ALERT_TIME = 0
ALERT_INTERVAL = 300  # 5 นาที = 300 วินาที

# เริ่มต้น Firebase
cred = credentials.Certificate(SERVICE_ACCOUNT_JSON)
firebase_admin.initialize_app(cred)
db = firestore.client()

def send_email_alert(subject, body):
    """ฟังก์ชันส่งอีเมลแจ้งเตือนผ่าน Gmail"""
    global LAST_ALERT_TIME
    now = time.time()
    if now - LAST_ALERT_TIME < ALERT_INTERVAL:
        print("ข้ามการส่งอีเมล (กันสแปม)")
        return
    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_USER
        msg["To"] = ALERT_EMAIL_TO
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        print("ส่งอีเมลแจ้งเตือนแล้ว")
        LAST_ALERT_TIME = now
    except Exception as e:
        print("เกิดข้อผิดพลาดในการส่งอีเมล:", e)

def check_internet():
    """ฟังก์ชันตรวจสอบว่า internet ใช้งานได้จริงหรือไม่
       จะ ping 3 ครั้งใน 5 วิ"""
    success_count = 0
    for i in range(3):
        try:
            delay = ping3.ping("8.8.8.8", timeout=2)  # ping google DNS
            if delay is not None:
                success_count += 1
        except Exception:
            pass
        time.sleep(1.5)  # เว้นเล็กน้อย

    return success_count >= 2  # ถือว่าผ่านถ้าได้ >=2 ครั้ง

def log_status(is_up):
    """บันทึก log ลง Firestore"""
    try:
        log_ref = db.collection("network_logs").document()
        log_ref.set({
            "timestamp": datetime.datetime.utcnow(),
            "status": "UP" if is_up else "DOWN"
        })
        print("บันทึก log สำเร็จ:", "UP" if is_up else "DOWN")
    except Exception as e:
        print("เกิดข้อผิดพลาดขณะส่ง log ไป Firestore:", e)

def main():
    print("เริ่มการตรวจสอบการเชื่อมต่ออินเทอร์เน็ต...")
    while True:
        is_up = check_internet()
        log_status(is_up)

        if not is_up:
            send_email_alert(
                "⚠️ Internet ล่ม",
                "ระบบตรวจพบว่าอินเทอร์เน็ตล่ม ณ เวลา {}".format(datetime.datetime.now())
            )
        time.sleep(60)  # เช็กทุกๆ 1 นาที

if __name__ == "__main__":
    main()
