import os
import sys
import json
import requests
from datetime import datetime, timedelta

# === Конфигурация ===
YONOTE_API_KEY = os.getenv("YONOTE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not all([YONOTE_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    print("❌ Отсутствуют обязательные переменные окружения", file=sys.stderr)
    sys.exit(1)

DATABASE_ID = "a5df07a4-cfda-47f5-b492-46d8b3e89e82"
STATUS_PROP_ID = "785c7c06-cd02-4de7-8380-48fec50d0cad"
DEADLINE_PROP_ID = "dc0ab42d-ff64-4641-bc2e-385e398e4428"

# ID статусов: Backlog, To do
TARGET_STATUS_IDS = [
    "fee81a83-81ef-40e0-b7a3-e5d72740fc47",  # Backlog
    "a0897724-3629-4880-9f1a-f4614d6f4256"   # To do
]

TODAY = datetime.utcnow().date()
DAYS_TO_CHECK = [1, 3]  # за 1 и 3 дня

def parse_date(date_str):
    """Преобразует 'YYYY/MM/DD' или 'YYYY-MM-DD' в date."""
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload)
    if not resp.ok:
        print(f"⚠️ Ошибка отправки в Telegram: {resp.text}", file=sys.stderr)

def main():
    # 1. Запрос к Yonote
    url = "https://app.yonote.ru/api/database.rows.list"
    headers = {
        "Authorization": f"Bearer {YONOTE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "parentDocumentId": DATABASE_ID,
        "filter": [{
            "filterPropertyId": STATUS_PROP_ID,
            "filterOperation": "IsEquals",
            "filterValue": TARGET_STATUS_IDS
        }]
    }

    resp = requests.post(url, headers=headers, json=payload)
    if not resp.ok:
        print(f"❌ Ошибка Yonote API: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    rows = data.get("data", [])

    messages = []

    for row in rows:
        title = row.get("title") or "Без названия"
        url_path = row.get("url", "")
        full_url = f"https://app.yonote.ru{url_path}" if url_path else ""

        values = row.get("values", {})
        status_ids = values.get(STATUS_PROP_ID, [])
        deadline_data = values.get(DEADLINE_PROP_ID)

        if not isinstance(status_ids, list) or not set(status_ids) & set(TARGET_STATUS_IDS):
            continue

        if not deadline_data or not isinstance(deadline_data, dict):
            continue

        date_str = deadline_data.get("from")
        if not date_str:
            continue

        deadline = parse_date(date_str)
        if not deadline:
            continue

        days_diff = (deadline - TODAY).days
        if days_diff not in DAYS_TO_CHECK:
            continue

        emoji = "⚠️" if days_diff == 1 else "🔔"
        when = "завтра" if days_diff == 1 else "через 3 дня"
        msg = f"{emoji} *{title}*\nДедлайн — {deadline.strftime('%Y-%m-%d')} ({when})\n{full_url}"
        messages.append(msg)

    if messages:
        full_text = "\n\n".join(messages)
        send_telegram_message(full_text)
        print(f"✅ Отправлено {len(messages)} напоминаний")
    else:
        print("ℹ️ Нет задач с дедлайном завтра или через 3 дня")

if __name__ == "__main__":
    main()