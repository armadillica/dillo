"""Contexts for notifications

Revision ID: 5747fc882218
Revises: 42809264a67e
Create Date: 2015-07-08 21:39:12.800457

"""

# revision identifiers, used by Alembic.
revision = '5747fc882218'
down_revision = '42809264a67e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('notification_object', sa.Column('context_object_id', sa.Integer(), nullable=True))
    op.add_column('notification_object', sa.Column('context_object_type_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('notification_object', 'context_object_type_id')
    op.drop_column('notification_object', 'context_object_id')
