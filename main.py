import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import db
from scheduler import create_scheduler
from telegram_auth import get_tg_initdata_header, validate_init_data

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")

scheduler = create_scheduler()


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    deadline: int = Field(description="UTC timestamp")


def get_user_id_from_header(init_data: str = Depends(get_tg_initdata_header)) -> int:
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="BOT_TOKEN is not configured")
    payload = validate_init_data(init_data, BOT_TOKEN)
    return payload["user_id"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    if BOT_TOKEN:
        scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Telegram Mini App Tasks API", lifespan=lifespan)

allowed_origins = [
    "https://web.telegram.org",
    "http://localhost:5500",
]
if FRONTEND_ORIGIN:
    allowed_origins.append(FRONTEND_ORIGIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/tasks")
def create_task(payload: TaskCreateRequest, user_id: int = Depends(get_user_id_from_header)):
    task = db.create_task(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        deadline=payload.deadline,
    )
    return task


@app.get("/tasks")
def list_tasks(
    filter: Literal["active", "today", "completed"] | None = Query(default=None),
    user_id: int = Depends(get_user_id_from_header),
):
    return db.get_tasks(user_id=user_id, task_filter=filter)


@app.post("/tasks/{task_id}/complete")
def complete_task(task_id: int, user_id: int = Depends(get_user_id_from_header)):
    task = db.complete_task(task_id=task_id, user_id=user_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, user_id: int = Depends(get_user_id_from_header)):
    deleted = db.delete_task(task_id=task_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@app.get("/leaderboard")
def leaderboard(_: int = Depends(get_user_id_from_header)):
    return db.get_leaderboard()
