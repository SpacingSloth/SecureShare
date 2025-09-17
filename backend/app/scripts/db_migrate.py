import subprocess
import sys

from sqlalchemy import create_engine, inspect

from app.core.database import DATABASE_URL


def main():
    sync_url = DATABASE_URL.replace("+aiosqlite", "")
    engine = create_engine(sync_url)
    insp = inspect(engine)

    has_alembic = insp.has_table("alembic_version")
    existing_core_tables = any(insp.has_table(t) for t in ("users", "files", "share_links"))

    if existing_core_tables and not has_alembic:
        print("[db-migrate] Existing tables detected without alembic_version → stamping head")
        subprocess.run(["alembic", "stamp", "head"], check=True)
    else:
        print(f"[db-migrate] has_alembic={has_alembic}, existing_core_tables={existing_core_tables}")

    subprocess.run(["alembic", "upgrade", "head"], check=True)

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"[db-migrate] Alembic command failed: {e}", file=sys.stderr)
        sys.exit(e.returncode)
    except Exception as e:
        print(f"[db-migrate] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)