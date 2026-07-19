"""token_version for token/session invalidation

Revision ID: 9c1b4e2f7a10
Revises: 8579324800c5
Create Date: 2026-07-19 00:00:00.000000

Adds an integer version counter to users and patients. Tokens embed the value
current at issue; bumping it on a password change/reset invalidates outstanding
sessions and makes reset/invite/portal tokens single-use once they set a
password. Backfilled to 0 for existing rows (matching tokens with no `tv`).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c1b4e2f7a10'
down_revision: Union[str, Sequence[str], None] = '8579324800c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'token_version',
                sa.Integer(),
                nullable=False,
                server_default='0',
            )
        )
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'token_version',
                sa.Integer(),
                nullable=False,
                server_default='0',
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.drop_column('token_version')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('token_version')
