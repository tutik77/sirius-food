"""promo usage once per user

Revision ID: 5c1e7a9d3f20
Revises: 974b236b0987
Create Date: 2026-11-28 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "5c1e7a9d3f20"
down_revision: Union[str, Sequence[str], None] = "974b236b0987"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_promo_code_usages_promo_user", "promo_code_usages", ["promo_code_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_promo_code_usages_promo_user", "promo_code_usages", type_="unique")
