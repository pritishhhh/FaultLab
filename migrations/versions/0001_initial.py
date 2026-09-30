"""Initial FaultLab schema.

Revision ID: 0001
Revises:
"""
from alembic import op
from faultlab.db import Base
from faultlab import models  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(op.get_bind())


def downgrade():
    Base.metadata.drop_all(op.get_bind())
