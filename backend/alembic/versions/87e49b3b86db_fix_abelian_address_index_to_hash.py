"""fix abelian_address index to hash

Revision ID: 87e49b3b86db
Revises: 6fbbb39e80d2
Create Date: 2026-02-28 15:32:03.948796
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '87e49b3b86db'
down_revision: Union[str, None] = '6fbbb39e80d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('DROP INDEX IF EXISTS ix_users_abelian_address')
    op.execute('CREATE INDEX ix_users_abelian_address_hash ON users USING hash (abelian_address)')
    op.execute(
        'CREATE UNIQUE INDEX uq_users_abelian_address ON users (md5(abelian_address)) '
        'WHERE abelian_address IS NOT NULL'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS uq_users_abelian_address')
    op.execute('DROP INDEX IF EXISTS ix_users_abelian_address_hash')
    op.create_unique_constraint('users_abelian_address_key', 'users', ['abelian_address'])
