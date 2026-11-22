import os
import sqlite3
from pathlib import Path
from typing import Literal, get_args

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", "votes.db")

AnswerType = Literal["good", "ok", "bad"]
ANSWERS = get_args(AnswerType)

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class Vote(BaseModel):
    answer: AnswerType


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS votes "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, answer TEXT NOT NULL)"
    )
    return conn


def get_stats():
    conn = _connect()
    rows = conn.execute("SELECT answer, COUNT(*) FROM votes GROUP BY answer").fetchall()
    conn.close()

    counts = {a: 0 for a in ANSWERS}
    counts.update(dict(rows))
    total = sum(counts.values())
    percents = {a: round(100 * c / total) if total else 0 for a, c in counts.items()}
    return {"total": total, "counts": counts, "percents": percents}


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.post("/vote")
def vote(v: Vote):
    conn = _connect()
    conn.execute("INSERT INTO votes (answer) VALUES (?)", (v.answer,))
    conn.commit()
    conn.close()
    return get_stats()


@app.get("/stats")
def stats():
    return get_stats()


@app.get("/health")
def health():
    return {"status": "ok"}