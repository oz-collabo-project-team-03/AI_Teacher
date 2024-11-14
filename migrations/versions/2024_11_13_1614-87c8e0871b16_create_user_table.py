"""Create User Table

Revision ID: 87c8e0871b16
Revises: 5a72f2c8b17c
Create Date: 2024-11-13 16:14:45.257260

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "87c8e0871b16"
down_revision: Union[str, None] = "5a72f2c8b17c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
