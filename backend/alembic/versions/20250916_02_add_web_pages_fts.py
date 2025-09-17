from alembic import op
import sqlalchemy as sa

revision = "20250916_add_web_pages_fts"
down_revision = "20250916_add_user_flags"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "web_pages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("file_id", sa.String(length=36), sa.ForeignKey("files.id"), nullable=False, index=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.execute("""
        CREATE VIRTUAL TABLE web_page_fts
        USING fts5(
            page_id UNINDEXED,
            title,
            body,
            safe_html,
            content=''
        );
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS web_page_fts;")
    op.drop_table("web_pages")
