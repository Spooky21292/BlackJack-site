# Telegram Mini App Backend (Tasks + Deadlines)

Простой backend для Telegram WebApp (Mini App) на **FastAPI + SQLite**.

## Стек
- Python 3.11
- FastAPI
- SQLite (файл `tasks.db`)
- APScheduler (проверка дедлайнов каждую минуту)

## Структура
- `main.py` — FastAPI приложение и роуты
- `db.py` — работа с SQLite
- `scheduler.py` — фоновые уведомления через Telegram Bot API
- `telegram_auth.py` — валидация `initData` из Telegram WebApp
- `requirements.txt`
- `.env.example`
- `Procfile`

## Переменные окружения (Railway)
Нужно добавить в Railway Variables:
- `BOT_TOKEN` — токен Telegram бота
- `FRONTEND_ORIGIN` — домен фронтенда (например `https://your-app.vercel.app`)
- `TIMEZONE` — `UTC` или `Europe/Moscow`

Пример значений есть в `.env.example`.

## Локальный запуск
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export BOT_TOKEN="<your_bot_token>"
export FRONTEND_ORIGIN="http://localhost:5500"
export TIMEZONE="UTC"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Деплой на Railway (пошагово)
1. Создайте новый проект в Railway.
2. Подключите GitHub-репозиторий с этим backend.
3. В разделе **Variables** добавьте:
   - `BOT_TOKEN`
   - `FRONTEND_ORIGIN`
   - `TIMEZONE`
4. Убедитесь, что в корне есть `Procfile`:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Railway автоматически запустит деплой после пуша.

## Проверка после деплоя
После успешного деплоя откройте:
- `https://<your-railway-domain>/health` — должен вернуть `{ "ok": true }`
- `https://<your-railway-domain>/docs` — Swagger UI

## Что делать, если Railway пишет "start.sh not found"
Это означает, что Railway пытается запускать несуществующий скрипт.

Решение:
1. Проверьте, что в корне есть `Procfile`.
2. Проверьте, что `Procfile` содержит ровно:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. Удалите/не используйте `start.sh`, если он не нужен.
4. Перезапустите деплой (Redeploy).

## Авторизация запросов
Клиент обязан передавать заголовок:
- `X-TG-INITDATA: <telegram_init_data>`

Backend:
- валидирует подпись `initData` через HMAC SHA256 и `BOT_TOKEN`
- достаёт `user.id`
- использует его как `user_id`
- отдаёт/изменяет только задачи владельца

## Эндпоинты
- `GET /health`
- `POST /tasks`
- `GET /tasks?filter=active|today|completed`
- `POST /tasks/{id}/complete`
- `DELETE /tasks/{id}`
- `GET /leaderboard`

## Уведомления
Фоновая задача (каждую минуту):
- за 24 часа до дедлайна
- за 1 час до дедлайна
- в момент дедлайна (и авто-завершение задачи)

Повторные уведомления не отправляются (через флаги `notified_24h`, `notified_1h`, `notified_deadline`).
