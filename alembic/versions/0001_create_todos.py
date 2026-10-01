"""create todos table

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("remind_at", sa.DateTime(), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_todos_completed", "todos", ["completed"])
    op.create_index("ix_todos_remind_at", "todos", ["remind_at"])


def downgrade() -> None:
    op.drop_index("ix_todos_remind_at", table_name="todos")
    op.drop_index("ix_todos_completed", table_name="todos")
    op.drop_table("todos")
