"""Change semester type to ARRAY(Integer)

Revision ID: d468657ef013
Revises: e1bc36d559b9
Create Date: 2025-04-04 22:57:35.377849

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd468657ef013'
down_revision: Union[str, None] = 'e1bc36d559b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
