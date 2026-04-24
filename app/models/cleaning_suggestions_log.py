import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class CleaningSuggestionsLog(Base):
    __tablename__ = "cleaning_suggestions_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    action_type = Column(String, doc="DROP_COLUMN, FILL_MEDIAN, REMOVE_DUPLICATES, etc.")
    target_column = Column(String)
    explanation = Column(Text, doc="LLM/Rule justification for the user")
    suggestion_status = Column(String, default="SUGGESTED", doc="SUGGESTED, APPROVED, REJECTED, EXECUTED, FAILED")
    applied_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="cleaning_suggestions_logs")
