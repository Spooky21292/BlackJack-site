import os
from datetime import datetime, timezone

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

import db

TELEGRAM_API_BASE = "https://api.telegram.org"
ADMIN_ID = 6109616823


class TaskScheduler:
    def __init__(self, bot_token: str, timezone_name: str = "UTC") -> None:
        self.bot_token = bot_token
        self.scheduler = BackgroundScheduler(timezone=ZoneInfo(timezone_name))
        self.last_update_id = 0

    def start(self) -> None:
        self.scheduler.add_job(self.process_notifications, "interval", minutes=1, id="notify_job")
        self.scheduler.add_job(self.process_bot_updates, "interval", seconds=5, id="updates_job")
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def send_message(self, chat_id: int, text: str) -> None:
        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        except requests.RequestException:
            pass

    def process_notifications(self) -> None:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        tasks = db.get_active_tasks_for_notifications()

        for task in tasks:
            time_left = task["deadline"] - now_ts
            title = task["title"]
            user_id = task["user_id"]

            if time_left <= 0 and not task["notified_deadline"]:
                self.send_message(user_id, f"⏰ Дедлайн наступил: {title}. Задача завершена автоматически.")
                db.mark_notification(task["id"], "notified_deadline")
                db.complete_task_by_system(task["id"])
                continue

            if time_left <= 3600 and not task["notified_1h"]:
                self.send_message(user_id, f"⌛ До дедлайна 1 час: {title}")
                db.mark_notification(task["id"], "notified_1h")

            if time_left <= 86400 and not task["notified_24h"]:
                self.send_message(user_id, f"📌 До дедлайна 24 часа: {title}")
                db.mark_notification(task["id"], "notified_24h")

    def process_bot_updates(self) -> None:
        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/getUpdates"
        params = {"timeout": 0, "offset": self.last_update_id + 1}

        try:
            response = requests.get(url, params=params, timeout=10)
            payload = response.json()
        except Exception:
            return

        if not payload.get("ok"):
            return

        for upd in payload.get("result", []):
            self.last_update_id = max(self.last_update_id, upd.get("update_id", 0))
            message = upd.get("message", {})
            text = (message.get("text") or "").strip()
            chat_id = message.get("chat", {}).get("id")
            from_user = message.get("from", {})
            from_id = from_user.get("id")

            if text == "/stats":
                if from_id != ADMIN_ID:
                    self.send_message(chat_id, "⛔ Команда доступна только администратору.")
                    continue

                stats = db.get_stats()
                lines = [
                    "📊 Статистика бота",
                    f"Пользователей: {stats['total_users']}",
                    f"Всего задач: {stats['total_tasks']}",
                    f"Завершённых задач: {stats['completed_tasks']}",
                    "",
                    "👥 Пользователи:",
                ]

                for user in stats["users"][:100]:
                    username = f"@{user['username']}" if user["username"] else "(без username)"
                    first_name = user["first_name"] or ""
                    lines.append(f"- {username} | {first_name} | id:{user['user_id']}")

                self.send_message(chat_id, "\n".join(lines))


def create_scheduler() -> TaskScheduler:
    return TaskScheduler(bot_token=os.getenv("BOT_TOKEN", ""), timezone_name=os.getenv("TIMEZONE", "UTC"))
