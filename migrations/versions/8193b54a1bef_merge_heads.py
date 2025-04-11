"""Merge heads

Revision ID: 8193b54a1bef
Revises: 7431ac931531, d2c7d2edfb31
Create Date: 2025-04-11 23:38:55.522987

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8193b54a1bef'
down_revision: Union[str, None] = ('7431ac931531', 'd2c7d2edfb31')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
