import os
from pathlib import Path

import psycopg

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    conn.execute("SELECT pg_advisory_xact_lock(731914)")
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY)")
    for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
        if not conn.execute("SELECT 1 FROM schema_migrations WHERE name = %s", (path.name,)).fetchone():
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations VALUES (%s)", (path.name,))
