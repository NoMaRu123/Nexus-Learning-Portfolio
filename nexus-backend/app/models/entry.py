"""LearningEntry ORM model.

Represents a timestamped progress log entry linked to exactly one
SkillRecord or ProjectRecord (enforced via check constraint).
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LearningEntry(Base):
    """A timestamped learning progress entry."""

    __tablename__ = "learning_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("skill_records.id", ondelete="CASCADE"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_records.id", ondelete="CASCADE"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entry_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    skill: Mapped["SkillRecord | None"] = relationship(
        back_populates="learning_entries"
    )
    project: Mapped["ProjectRecord | None"] = relationship(
        back_populates="learning_entries"
    )

    __table_args__ = (
        CheckConstraint(
            "(skill_id IS NOT NULL AND project_id IS NULL) OR "
            "(skill_id IS NULL AND project_id IS NOT NULL)",
            name="ck_entry_single_parent",
        ),
    )
