"""add embeddings

Revision ID: 6c43fee2e8d6
Revises: 4dd3884e3384
Create Date: 2024-05-29 14:04:13.911722

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c43fee2e8d6"
down_revision: str | None = "4dd3884e3384"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "video",
        sa.Column("embedding", sa.ARRAY(sa.Float(), dimensions=1), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("video", "embedding")
    # ### end Alembic commands ###
