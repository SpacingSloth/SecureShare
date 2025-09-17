from alembic import op
import sqlalchemy as sa

revision = "20250916_add_user_flags"
down_revision = "202509131822_ec4fbc03"  
branch_labels = None
depends_on = None

def _has_column(conn, table, column):
    rows = conn.exec_driver_sql(f"PRAGMA table_info({table});").fetchall()
    return any(r[1] == column for r in rows)

def upgrade():
    conn = op.get_bind()

    cols = [
        ("email_verified", sa.Boolean(), "0", False),
        ("two_factor_enabled", sa.Boolean(), "0", False),
        ("two_factor_secret", sa.String(255), None, True),
        ("force_password_reset", sa.Boolean(), "0", False),
        ("is_2fa_enabled", sa.Boolean(), "0", False),
        ("otp_secret", sa.String(255), None, True),
    ]

    for name, coltype, default, nullable in cols:
        if not _has_column(conn, "users", name):
            if default is None:
                op.add_column("users", sa.Column(name, coltype, nullable=nullable))
            else:
                op.add_column(
                    "users",
                    sa.Column(name, coltype, nullable=nullable, server_default=sa.text(default))
                )

def downgrade():
    with op.batch_alter_table("users") as batch:
        for name in ["otp_secret","is_2fa_enabled","force_password_reset","two_factor_secret","two_factor_enabled","email_verified"]:
            try:
                batch.drop_column(name)
            except Exception:
                pass
