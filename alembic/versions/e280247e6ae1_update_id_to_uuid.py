"""update id to uuid

Revision ID: e280247e6ae1
Revises: a23d5aace1a6
Create Date: 2024-05-08 23:24:19.786187

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e280247e6ae1"
down_revision: str | None = "a23d5aace1a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "playlist_video_playlist_id_fkey", "playlist_video", type_="foreignkey"
    )

    op.execute("ALTER TABLE playlist ALTER COLUMN id TYPE UUID USING (id::uuid)")

    op.execute(
        "ALTER TABLE playlist_video ALTER COLUMN playlist_id TYPE UUID USING (playlist_id::uuid)"
    )

    op.create_foreign_key(
        "playlist_video_playlist_id_fkey",
        "playlist_video",
        "playlist",
        ["playlist_id"],
        ["id"],
    )

    op.drop_index("ix_playlist_id", table_name="playlist")
    op.create_index("ix_playlist_id", "playlist", ["id"], unique=False)


def downgrade() -> None:
    op.drop_constraint(
        "playlist_video_playlist_id_fkey", "playlist_video", type_="foreignkey"
    )

    op.execute(
        "ALTER TABLE playlist_video ALTER COLUMN playlist_id TYPE VARCHAR USING (playlist_id::text)"
    )

    op.execute("ALTER TABLE playlist ALTER COLUMN id TYPE VARCHAR USING (id::text)")

    op.create_foreign_key(
        "playlist_video_playlist_id_fkey",
        "playlist_video",
        "playlist",
        ["playlist_id"],
        ["id"],
    )

    op.drop_index("ix_playlist_id", table_name="playlist")
    op.create_index("ix_playlist_id", "playlist", ["id"], unique=False)
