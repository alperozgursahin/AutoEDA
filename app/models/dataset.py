import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, doc="Path to raw CSV/XLSX")
    cleaned_file_path = Column(String, doc="Path to versioned clean data")
    report_file_path = Column(String, doc="Path to PDF/HTML report")
    file_size_bytes = Column(Integer)
    is_deleted = Column(Boolean, default=False, doc="Soft delete")
    status = Column(String, default="UPLOADED", doc="UPLOADED, PROFILING, AWAITING_APPROVAL, CLEANING, DONE, FAILED")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="datasets")
    profiling_result = relationship("ProfilingResult", back_populates="dataset", uselist=False)
    cleaning_suggestions_logs = relationship("CleaningSuggestionsLog", back_populates="dataset")
