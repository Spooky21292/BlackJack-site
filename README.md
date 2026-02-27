# Telegram Mini App: Frontend + Backend

Проект содержит:
- статический фронтенд (`index.html`, `styles.css`, `app.js`) для Timeweb
- backend (`main.py`, `db.py`, `scheduler.py`, `telegram_auth.py`) на FastAPI + SQLite

## Важно: API URL во фронтенде
В `app.js` укажите ваш Railway backend:

```js
const API_BASE = "https://PASTE_YOUR_RAILWAY_DOMAIN_HERE";
```

## Лидерборд по @username
Backend теперь хранит пользователей из Telegram `initData` и в `/leaderboard` возвращает:
- `display_name` (приоритет: `@username`, потом `first_name`, потом `id:...`)
- `completed_count`

Фронтенд в лидерборде показывает именно `display_name`.

## Команда /stats только для admin id
Реализовано ограничение для `user_id = 6109616823`:
- HTTP endpoint: `GET /stats` (только для admin)
- Telegram команда: `/stats` (через polling `getUpdates`, только для admin)

`/stats` показывает:
- сколько уникальных пользователей заходило
- сколько всего задач и завершённых
- список пользователей (username, first_name, id)

## Railway backend deploy
1. Загрузите репозиторий в Railway.
2. Добавьте переменные окружения:
   - `BOT_TOKEN`
   - `FRONTEND_ORIGIN` (домен фронтенда на Timeweb)
   - `TIMEZONE` (`UTC` или `Europe/Moscow`)
3. Убедитесь, что есть `Procfile`:
   `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Деплой.

## Timeweb frontend deploy
1. Залейте `index.html`, `styles.css`, `app.js` в корень сайта.
2. В `app.js` вставьте Railway URL backend.
3. В BotFather укажите URL фронтенда как WebApp URL.

## Проверка
- Backend: `https://<railway>/health`
- Swagger: `https://<railway>/docs`
- Mini App открывать только внутри Telegram.

## Если ошибка запроса
1. Проверьте `API_BASE` в `app.js`.
2. Проверьте `/health` backend.
3. Проверьте, что открываете именно из Telegram (нужен валидный `initData`).
4. Проверьте `BOT_TOKEN` и `FRONTEND_ORIGIN` на Railway.
