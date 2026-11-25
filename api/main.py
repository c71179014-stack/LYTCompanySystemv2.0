import os
from dataclasses import dataclass
from typing import Callable

import boto3
import httpx
import psycopg
import redis
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app

app = FastAPI(title="LYT Company System")
app.mount("/metrics", make_asgi_app())


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ready")
def ready():
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=2) as conn:
            conn.execute("SELECT 1 FROM documents LIMIT 1")
        with redis.Redis.from_url(os.environ["REDIS_URL"], socket_timeout=2, socket_connect_timeout=2) as cache:
            cache.ping()
    except (KeyError, psycopg.Error, redis.RedisError):
        raise HTTPException(503, "Dependencies are not ready") from None
    return {"status": "ready"}


def s3_client():
    return boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT_URL"))


def embeddings(text: str) -> list[float]:
    response = httpx.post(
        os.environ["MODEL_BASE_URL"].rstrip("/") + "/embeddings",
        headers={"Authorization": "Bearer " + os.environ["MODEL_API_KEY"]},
        json={"input": text, "model": os.environ["EMBEDDING_MODEL"]},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def retrieve(query: str) -> list[str]:
    vector = embeddings(query)
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=2) as conn:
        rows = conn.execute(
            """SELECT body FROM documents WHERE vector_dims(embedding) = %s
            ORDER BY CASE WHEN vector_dims(embedding) = %s THEN embedding <=> %s::vector END
            LIMIT 5""",
            (len(vector), len(vector), str(vector)),
        ).fetchall()
    return [row[0] for row in rows]


@dataclass(frozen=True)
class Tool:
    run: Callable[..., object]
    requires_approval: bool = True


TOOLS: dict[str, Tool] = {}


def run_tool(name: str, arguments: dict):
    tool = TOOLS[name]
    if tool.requires_approval:
        raise PermissionError("Approval backend is not configured")
    return tool.run(**arguments)


def record_audit(actor: str, action: str):
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=2) as conn:
        conn.execute("INSERT INTO audit_events (actor, action) VALUES (%s, %s)", (actor, action))
