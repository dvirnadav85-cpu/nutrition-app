"""
Evening reminder script — run daily via Windows Task Scheduler.
Sends a WhatsApp message to mom if she hasn't logged any meals today.
"""
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv

# Load .env from the same folder as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

import httpx
from twilio.rest import Client

LOG_FILE = os.path.join(script_dir, "reminder_log.txt")

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def count_meals_today() -> int:
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY", "")
    today = date.today().isoformat()
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    r = httpx.get(
        f"{url}/rest/v1/meal_log",
        headers=headers,
        params={"meal_date": f"eq.{today}", "select": "id"},
    )
    r.raise_for_status()
    return len(r.json())

def send_whatsapp(message: str):
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )
    client.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=os.getenv("TWILIO_WHATSAPP_TO"),
        body=message,
    )

def main():
    log("Reminder check started")
    try:
        count = count_meals_today()
        log(f"Meals logged today: {count}")

        if count == 0:
            msg = (
                "שלום מירה! 🌙\n"
                "נראה שעוד לא תיעדת ארוחות היום.\n"
                "כדאי לפתוח את האפליקציה ולספר לי מה אכלת — גם אם זה רק חטיף קטן 😊"
            )
            send_whatsapp(msg)
            log("Reminder sent ✅")
        else:
            log(f"No reminder needed — {count} meal(s) already logged today.")

    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
