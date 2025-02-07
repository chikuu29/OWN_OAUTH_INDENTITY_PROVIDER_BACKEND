"""Added fields to OAuthClient

Revision ID: 8e530b2649ef
Revises: 053abe8911e8
Create Date: 2025-02-07 07:04:49.316735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e530b2649ef'
down_revision: Union[str, None] = '053abe8911e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('oauth_clients', 'name',
                existing_type=sa.String(), 
                nullable=True)  # Keep as String and make it nullable
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('oauth_clients', 'name',
                existing_type=sa.String(), 
                nullable=True)  # Keep as String and make it nullable
    # ### end Alembic commands ###
