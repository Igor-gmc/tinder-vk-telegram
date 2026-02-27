"""init

Revision ID: 620c17140cdd
Revises:
Create Date: 2026-02-25 23:54:36.414984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '620c17140cdd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('blacklist',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tg_user_id', sa.BigInteger(), nullable=False),
    sa.Column('vk_profile_id', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tg_user_id', 'vk_profile_id')
    )
    op.create_table('favorites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tg_user_id', sa.BigInteger(), nullable=False),
    sa.Column('vk_profile_id', sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tg_user_id', 'vk_profile_id')
    )
    op.create_table('profiles',
    sa.Column('vk_user_id', sa.BigInteger(), nullable=False),
    sa.Column('first_name', sa.String(), nullable=False),
    sa.Column('last_name', sa.String(), nullable=False),
    sa.Column('domain', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('vk_user_id')
    )
    op.create_table('users',
    sa.Column('tg_user_id', sa.BigInteger(), nullable=False),
    sa.Column('vk_access_token', sa.String(), nullable=True),
    sa.Column('vk_user_id', sa.BigInteger(), nullable=True),
    sa.Column('filter_city_name', sa.String(), nullable=True),
    sa.Column('filter_city_id', sa.Integer(), nullable=True),
    sa.Column('filter_gender', sa.Integer(), nullable=True),
    sa.Column('filter_age_from', sa.Integer(), nullable=True),
    sa.Column('filter_age_to', sa.Integer(), nullable=True),
    sa.Column('history_cursor', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('tg_user_id')
    )
    op.create_table('photos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vk_user_id', sa.BigInteger(), nullable=False),
    sa.Column('photo_id', sa.BigInteger(), nullable=False),
    sa.Column('owner_id', sa.BigInteger(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('likes_count', sa.Integer(), nullable=False),
    sa.Column('local_path', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['vk_user_id'], ['profiles.vk_user_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('queue',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tg_user_id', sa.BigInteger(), nullable=False),
    sa.Column('vk_profile_id', sa.BigInteger(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tg_user_id'], ['users.tg_user_id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('queue')
    op.drop_table('photos')
    op.drop_table('users')
    op.drop_table('profiles')
    op.drop_table('favorites')
    op.drop_table('blacklist')
