"""Fix curriculum table schema

Revision ID: 051cbf10d468
Revises: 5ccd78ba54f8
Create Date: 2025-03-23 11:21:31.183386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '051cbf10d468'
down_revision: Union[str, None] = '5ccd78ba54f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('curriculum', sa.Column('curriculum_id', sa.Integer(), nullable=False))
    op.drop_column('curriculum', 'id')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('curriculum', sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False))
    op.drop_column('curriculum', 'curriculum_id')
    # ### end Alembic commands ###
