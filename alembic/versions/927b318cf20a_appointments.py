"""Mock clinic appointments and durable voice booking state.

Revision ID: 927b318cf20a
Revises: 0168038b9c35
"""

import sqlalchemy as sa

from alembic import op

revision = "927b318cf20a"
down_revision = "0168038b9c35"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "appointments",
        sa.Column("appointment_id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.patient_id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["starts_at"],
        unique=True,
        postgresql_where=sa.text("cancelled_at IS NULL"),
        sqlite_where=sa.text("cancelled_at IS NULL"),
    )
    op.add_column("registrations", sa.Column("booking_patient_id", sa.Uuid()))
    op.add_column("registrations", sa.Column("appointment_slot", sa.DateTime(timezone=True)))
    op.add_column("registrations", sa.Column("appointment_token", sa.String(36)))
    op.add_column("registrations", sa.Column("appointment_id", sa.Uuid()))


def downgrade():
    for column in ("appointment_id", "appointment_token", "appointment_slot", "booking_patient_id"):
        op.drop_column("registrations", column)
    op.drop_table("appointments")
