"""add password_hash, roles, refresh_tokens

Revision ID: 508b885c512e
Revises: 525f51d7b14a
Create Date: 2026-10-16 17:29:39.565036

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '508b885c512e'
down_revision: Union[str, Sequence[str], None] = '525f51d7b14a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Заглушка для пользователей, созданных до появления паролей. Это не bcrypt-хеш,
# поэтому verify_password для неё всегда возвращает False: войти такой
# пользователь не сможет, пока администратор не задаст ему пароль.
UNUSABLE_PASSWORD = "!"


def upgrade() -> None:
    """Таблицы ролей и refresh-токенов, пароль и роль у пользователя."""
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), unique=True, nullable=False),
    )

    # Колонки добавляем nullable: в users уже могут быть строки.
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("role_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_users_role", "users", "roles", ["role_id"], ["id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # Сумма заказа фиксируется при оформлении, чтобы при отмене вернуть ровно её.
    op.add_column("orders", sa.Column("total_cost", sa.Float(), nullable=True))

    op.execute("INSERT INTO roles (name) VALUES ('student'), ('cook'), ('courier'), ('admin')")

    # Существующим пользователям — роль student и непригодный для входа пароль.
    op.execute("UPDATE users SET role_id = (SELECT id FROM roles WHERE name = 'student')")
    op.execute(f"UPDATE users SET password_hash = '{UNUSABLE_PASSWORD}'")
    # Старым заказам — сумма по текущей цене блюда.
    op.execute(
        "UPDATE orders SET total_cost = menu_items.price * orders.quantity "
        "FROM menu_items WHERE menu_items.id = orders.item_id"
    )

    # Теперь колонки можно сделать обязательными.
    op.alter_column("users", "role_id", nullable=False)
    op.alter_column("users", "password_hash", nullable=False)


def downgrade() -> None:
    op.drop_column("orders", "total_cost")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_constraint("fk_users_role", "users", type_="foreignkey")
    op.drop_column("users", "role_id")
    op.drop_column("users", "password_hash")
    op.drop_table("roles")
