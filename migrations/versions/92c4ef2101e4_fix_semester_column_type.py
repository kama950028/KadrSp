"""fix_semester_column_type

Revision ID: 92c4ef2101e4
Revises: f4984de3391f
Create Date: 2025-03-23 22:10:48.149417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92c4ef2101e4'
down_revision: Union[str, None] = 'f4984de3391f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
