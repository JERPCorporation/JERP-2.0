"""
JERP 2.0 - Audit Log Model
Immutable audit trail with SHA-256 hash chain for compliance
"""
import hashlib
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class AuditLog(Base):
    """
    Immutable audit log with cryptographic hash chain.
    Each record links to the previous via SHA-256 hash for tamper detection.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="audit_logs")
    user_email = Column(String(255), nullable=True)
    
    # What action was performed
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    
    # Details of the change
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Hash chain for immutability
    previous_hash = Column(String(64), nullable=True, index=True)
    current_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog(id={{self.id}}, action='{{self.action}}', resource='{{self.resource_type}}')>"

    @staticmethod
    def compute_hash(
        previous_hash: str,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: str,
        old_values: dict,
        new_values: dict,
        timestamp: datetime
    ) -> str:
        """Compute SHA-256 hash for audit log entry."""
        data = f"{{previous_hash or 'GENESIS'}}|{{user_id}}|{{action}}|{{resource_type}}|{{resource_id}}|{{old_values}}|{{new_values}}|{{timestamp.isoformat()}}"
        return hashlib.sha256(data.encode()).hexdigest()

    @classmethod
    def create_entry(
        cls,
        user_id: int,
        user_email: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        old_values: dict = None,
        new_values: dict = None,
        description: str = None,
        ip_address: str = None,
        user_agent: str = None,
        previous_hash: str = None
    ) -> "AuditLog":
        """Factory method to create a new audit log entry with computed hash."""
        timestamp = datetime.utcnow()
        current_hash = cls.compute_hash(
            previous_hash, user_id, action, resource_type,
            resource_id, old_values, new_values, timestamp
        )
        
        return cls(
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=previous_hash,
            current_hash=current_hash,
            created_at=timestamp
        )