"""Run against a fresh, disposable PostgreSQL database and Redis instance."""
import os
import runpy
import time
from unittest.mock import patch

import psycopg
import redis
from fastapi.testclient import TestClient

from main import app, record_audit, retrieve


def main():
    db = os.environ["DATABASE_URL"]
    cache = os.environ["REDIS_URL"]
    for attempt in range(30):
        try:
            with psycopg.connect(db, connect_timeout=2) as conn:
                conn.execute("SELECT 1")
            with redis.Redis.from_url(cache, socket_connect_timeout=2, socket_timeout=2) as client:
                client.ping()
            break
        except (psycopg.Error, redis.RedisError):
            if attempt == 29:
                raise
            time.sleep(1)

    runpy.run_module("migrate", run_name="__main__")
    runpy.run_module("migrate", run_name="__main__")
    client = TestClient(app)
    response = client.get("/api/ready")
    assert response.status_code == 200 and response.json() == {"status": "ready"}
    with patch("main.redis.Redis.from_url", side_effect=redis.ConnectionError):
        assert client.get("/api/ready").status_code == 503

    with psycopg.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM schema_migrations").fetchone()[0] == 1
        conn.execute(
            "INSERT INTO documents(body, embedding) VALUES "
            "('near', '[1,0]'), ('far', '[0,1]'), ('other dimension', '[1,0,0]')"
        )
    with patch("main.embeddings", return_value=[1, 0]):
        assert retrieve("query") == ["near", "far"]
    record_audit("acceptance-user", "smoke")
    with psycopg.connect(db) as conn:
        assert conn.execute(
            "SELECT action FROM audit_events WHERE actor = %s", ("acceptance-user",)
        ).fetchone() == ("smoke",)
    assert "python_info" in client.get("/metrics/").text
    print("PASS: migration, readiness, dependency failure, vector retrieval, audit, metrics")


if __name__ == "__main__":
    main()
