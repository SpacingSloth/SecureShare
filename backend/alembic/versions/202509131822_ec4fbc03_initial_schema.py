from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202509131822_ec4fbc03"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('email', sa.String(), nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('force_password_reset', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_2fa_enabled', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('otp_secret', sa.String(), nullable=True),
    )

    op.create_table(
        'files',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('filename', sa.String(), index=True),
        sa.Column('content_type', sa.String()),
        sa.Column('size', sa.Integer()),
        sa.Column('owner_id', sa.String(length=36), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('bucket', sa.String(), nullable=True),
        sa.Column('object_name', sa.String(), nullable=True),
    )

    op.create_table(
        'share_links',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('file_id', sa.String(length=36), sa.ForeignKey('files.id')),
        sa.Column('token', sa.String(), unique=True, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('max_views', sa.Integer(), nullable=True),
        sa.Column('views', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
    )

def downgrade() -> None:
    op.drop_table('share_links')
    op.drop_table('files')
    op.drop_table('users')