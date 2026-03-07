"""
Script to set up the PostgreSQL database for SteerPlane.
Run once after installing PostgreSQL.

Usage:
    python setup_postgres.py
"""

import subprocess
import sys
import os

PSQL = r"C:\Program Files\PostgreSQL\17\bin\psql.exe"
CREATEDB = r"C:\Program Files\PostgreSQL\17\bin\createdb.exe"

DB_NAME = "steerplane"
DB_USER = "steerplane"
DB_PASS = "steerplane"


def run_psql(sql, user="postgres", db="postgres"):
    """Execute SQL via psql."""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASS  # For steerplane user
    result = subprocess.run(
        [PSQL, "-U", user, "-d", db, "-c", sql],
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def setup():
    print("Setting up PostgreSQL for SteerPlane...")
    print(f"  Database: {DB_NAME}")
    print(f"  User:     {DB_USER}")
    print()

    # Try to create user (may already exist)
    result = run_psql(
        f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASS}';",
        user="postgres",
    )
    if "already exists" in (result.stderr or ""):
        print("[OK] User already exists")
    elif result.returncode == 0:
        print("[OK] User created")
    else:
        print(f"[WARN] User creation: {result.stderr.strip()}")

    # Try to create database
    result = subprocess.run(
        [CREATEDB, "-U", "postgres", "-O", DB_USER, DB_NAME],
        capture_output=True,
        text=True,
    )
    if "already exists" in (result.stderr or ""):
        print("[OK] Database already exists")
    elif result.returncode == 0:
        print("[OK] Database created")
    else:
        print(f"[WARN] Database creation: {result.stderr.strip()}")

    # Grant privileges
    run_psql(
        f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};",
        user="postgres",
    )
    print("[OK] Privileges granted")

    # Test connection
    print()
    print("Testing connection...")
    result = run_psql("SELECT 1 as test;", user=DB_USER, db=DB_NAME)
    if result.returncode == 0:
        print("[OK] Connection successful!")
        print()
        print("=" * 50)
        print("PostgreSQL is ready!")
        print()
        print("To use PostgreSQL with SteerPlane API, set:")
        print(f'  DATABASE_URL=postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}')
        print()
        print("Start API with:")
        print(f'  set DATABASE_URL=postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}')
        print(f'  uvicorn app.main:app --reload')
        print("=" * 50)
    else:
        print(f"[ERROR] Connection failed: {result.stderr}")
        print()
        print("You may need to set the postgres user password first:")
        print("  1. Open pgAdmin or run:")
        print(f'     "{PSQL}" -U postgres')
        print("  2. Set password: ALTER USER postgres PASSWORD 'yourpassword';")
        sys.exit(1)


if __name__ == "__main__":
    setup()
