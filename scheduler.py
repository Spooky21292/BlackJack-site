import os
from datetime import datetime, timezone

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from zoneinfo import ZoneInfo

import db

TELEGRAM_API_BASE = "https://api.telegram.org"


class TaskScheduler:
    def __init__(self, bot_token: str, timezone_name: str = "UTC") -> None:
        self.bot_token = bot_token
        self.timezone_name = timezone_name
        self.scheduler = BackgroundScheduler(timezone=ZoneInfo(timezone_name))

    def start(self) -> None:
        self.scheduler.add_job(self.process_notifications, "interval", minutes=1, id="notify_job")
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def send_message(self, chat_id: int, text: str) -> None:
        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        except requests.RequestException:
            # Silent fail to keep scheduler alive.
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


def create_scheduler() -> TaskScheduler:
    bot_token = os.getenv("BOT_TOKEN", "")
    timezone_name = os.getenv("TIMEZONE", "UTC")
    return TaskScheduler(bot_token=bot_token, timezone_name=timezone_name)
