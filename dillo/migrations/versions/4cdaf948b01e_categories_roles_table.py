"""categories_roles table

Revision ID: 4cdaf948b01e
Revises: 171f2b52ab25
Create Date: 2016-03-16 00:05:17.972836

"""

# revision identifiers, used by Alembic.
revision = '4cdaf948b01e'
down_revision = '171f2b52ab25'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('categories_roles',
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['category_id'], ['category.id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['role.id'], )
    )


def downgrade():
    op.drop_table('categories_roles')
