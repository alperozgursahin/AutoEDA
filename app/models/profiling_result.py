import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base

class ProfilingResult(Base):
    __tablename__ = "profiling_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    pre_cleaning_score = Column(Float, doc="Initial health score (0-100)")
    post_cleaning_score = Column(Float, doc="Score after approved transformations")
    dataset_statistics = Column(JSONB, doc="Metadata: row/col counts, global missing ratio")
    column_statistics = Column(JSONB, doc="Per-column: type, unique counts, outliers")
    detected_issues = Column(JSONB, doc="Diagnostic log of anomalies found")
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="profiling_result")
