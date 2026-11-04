"""widen api_keys.key_prefix

The stored prefix is 17 characters ("sk_sp_" + 8 + "..."), one more than the
column held. SQLite ignores the length, so this only failed on PostgreSQL, where
every key creation returned 500.

Revision ID: a7c1e94d2b60
Revises: 8efb7b655a22
Create Date: 2026-11-04 17:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c1e94d2b60"
down_revision: Union[str, None] = "8efb7b655a22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.alter_column(
            "key_prefix", existing_type=sa.String(16), type_=sa.String(32), existing_nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("api_keys") as batch_op:
        batch_op.alter_column(
            "key_prefix", existing_type=sa.String(32), type_=sa.String(16), existing_nullable=False
        )
