"""
SteerPlane API — database URL handling.
"""

from sqlalchemy.engine import make_url


def mask_database_password(url: str) -> str:
    """Return the URL with its password masked, for logs and console output."""
    try:
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        # Never echo a URL we could not parse; it may still contain a password.
        return "<DATABASE_URL set, not shown>"


def resolve_database_url(url: str) -> str:
    """Name the PostgreSQL driver explicitly.

    SQLAlchemy 2.1 changed the driver behind a bare ``postgresql://`` URL from
    psycopg2 to psycopg 3. The API ships with psycopg2 (see requirements.txt),
    so a bare URL stopped working on a fresh install. Pinning the driver keeps
    every SQLAlchemy 2.x release on psycopg2. ``postgres://`` (used by some
    hosting providers) is accepted too. URLs that already name a driver, and
    non-PostgreSQL URLs, are returned unchanged.
    """
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix) :]
    return url
