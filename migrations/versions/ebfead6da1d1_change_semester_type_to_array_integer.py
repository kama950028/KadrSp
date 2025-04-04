"""Change semester type to ARRAY(Integer)

Revision ID: ebfead6da1d1
Revises: 1a4c56870f7d
Create Date: 2025-04-04 22:34:46.364964

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ebfead6da1d1'
down_revision: Union[str, None] = '1a4c56870f7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column(
        'curriculum',
        'semester',
        existing_type=sa.INTEGER(),
        type_=postgresql.ARRAY(sa.INTEGER()),
        postgresql_using='semester::integer[]'
    )

def downgrade():
    op.alter_column(
        'curriculum',
        'semester',
        existing_type=postgresql.ARRAY(sa.INTEGER()),
        type_=sa.INTEGER()
    )
