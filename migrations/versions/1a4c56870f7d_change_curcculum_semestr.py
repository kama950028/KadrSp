"""change curcculum_Semestr

Revision ID: 1a4c56870f7d
Revises: da3f099f0449
Create Date: 2025-04-04 22:31:01.545337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a4c56870f7d'
down_revision: Union[str, None] = 'da3f099f0449'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
