import os
import logging
import threading
from contextlib import contextmanager
from pathlib import Path

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection pool — keeps warm connections alive so Neon doesn't cold-start
# on every request.  min=1 keeps one connection alive at all times.
# ---------------------------------------------------------------------------
_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()

# Timeouts (seconds)
_CONNECT_TIMEOUT = 15   # max time to establish a connection
_POOL_MIN = 1
_POOL_MAX = 10


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Add it to .env")
    return database_url


def _build_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Create and return a new connection pool."""
    url = get_database_url()
    return psycopg2.pool.ThreadedConnectionPool(
        _POOL_MIN,
        _POOL_MAX,
        url,
        cursor_factory=RealDictCursor,
        connect_timeout=_CONNECT_TIMEOUT,
    )


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Return the global pool, initialising it lazily on first call."""
    global _pool
    if _pool is None or _pool.closed:
        with _pool_lock:
            if _pool is None or _pool.closed:
                logger.info("Initialising database connection pool…")
                _pool = _build_pool()
                logger.info("Connection pool ready.")
    return _pool


def _is_connection_alive(conn) -> bool:
    """Quick health-check: returns True if the connection can execute a query."""
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.autocommit = False
        return True
    except Exception:
        return False


@contextmanager
def get_connection():
    """
    Yield a psycopg2 connection from the pool.

    Before yielding, the connection is validated with a lightweight SELECT 1.
    If the underlying SSL socket was killed by Neon during sleep, the dead
    connection is discarded, the pool is rebuilt, and a fresh connection is
    obtained.  Up to 3 retries are attempted before falling back to a direct
    (non-pooled) connection.
    """
    global _pool
    conn = None
    from_pool = False
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            pool = get_pool()
            conn = pool.getconn()
            from_pool = True

            if _is_connection_alive(conn):
                conn.autocommit = False
                break  # healthy — use this connection

            # Dead connection — discard it and rebuild the pool
            logger.warning(
                "Stale pooled connection detected (attempt %d/%d). "
                "Discarding and rebuilding pool.",
                attempt, max_retries,
            )
            try:
                pool.putconn(conn, close=True)
            except Exception:
                pass
            conn = None
            from_pool = False

            # Tear down the entire pool so the next get_pool() builds fresh
            with _pool_lock:
                try:
                    _pool.closeall()
                except Exception:
                    pass
                _pool = None

        except psycopg2.pool.PoolError:
            logger.warning(
                "Pool unavailable (attempt %d/%d).", attempt, max_retries,
            )
            conn = None
            from_pool = False
    else:
        # All retries exhausted — fall back to a direct connection
        logger.warning("All pool retries exhausted. Opening direct connection.")
        conn = psycopg2.connect(
            get_database_url(),
            cursor_factory=RealDictCursor,
            connect_timeout=_CONNECT_TIMEOUT,
        )
        from_pool = False

    try:
        conn.autocommit = False
        yield conn
    finally:
        if conn is not None:
            if from_pool:
                try:
                    get_pool().putconn(conn)
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
            else:
                try:
                    conn.close()
                except Exception:
                    pass


def warmup() -> None:
    """
    Send a trivial query to keep the Neon instance awake.
    Call this once at startup so the first real request is fast.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        logger.info("Database warmup ping successful.")
    except Exception as exc:
        logger.warning("Database warmup ping failed (non-fatal): %s", exc)


def init_db() -> None:
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(schema_sql)
        conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
