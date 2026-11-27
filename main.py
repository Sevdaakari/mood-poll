import os
import sqlite3
import time
from pathlib import Path
from typing import Literal, get_args

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", "votes.db")

AnswerType = Literal["good", "ok", "bad"]
ANSWERS = get_args(AnswerType)

app = FastAPI()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# --- Prometheus metrics ---
REQUESTS = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["path"]
)
VOTES = Counter("mood_votes_total", "Number of votes by answer", ["answer"])


@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        path = route.path if route else "unmatched"
        if path != "/metrics":
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(path).observe(time.perf_counter() - start)


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
    VOTES.labels(v.answer).inc()
    return get_stats()


@app.get("/stats")
def stats():
    return get_stats()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)