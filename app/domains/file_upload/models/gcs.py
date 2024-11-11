from sqlalchemy import  Column,ForeignKey,String,Boolean,DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base_class import APIBase
from datetime import datetime



class FileUpload(APIBase):
    file_type = Column(String(255),nullable=True)
    url= Column(String(255),nullable=True)
    filename = Column(String(255),nullable=True)
    description = Column(String(255),nullable=True)
    type_of_upload = Column(String(255),nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_reason = Column(String(255),nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    users = relationship('User', back_populates='file_uploads')