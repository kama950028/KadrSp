"""Add final_work_hours to Curriculum

Revision ID: e0a3b66264c7
Revises: 92c4ef2101e4
Create Date: 2025-03-25 12:13:40.141250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0a3b66264c7'
down_revision: Union[str, None] = '92c4ef2101e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('curriculum', sa.Column('final_work_hours', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('curriculum', 'final_work_hours')
    # ### end Alembic commands ###
