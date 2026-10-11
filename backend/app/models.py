from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="farmer") # farmer, employee, admin
    
    diagnoses = relationship("Diagnosis", back_populates="owner")

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    image_filename = Column(String)
    prediction = Column(String)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="diagnoses")


class DiseaseContent(Base):
    __tablename__ = "disease_content"

    slug = Column(String, primary_key=True)
    draft_json = Column(Text, nullable=False)
    published_json = Column(Text)
    updated_by = Column(Integer, ForeignKey("users.id"))
    updated_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime)


class ClientActivity(Base):
    __tablename__ = "client_activity"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(String, nullable=False)
    app_version = Column(String, nullable=False)
    event = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ActiveClient(Base):
    __tablename__ = "active_clients"

    # HMAC of a random client-generated ID; never store the raw device ID.
    key = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String(16), nullable=False)
    app_version = Column(String(40), nullable=False)
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AdminAudit(Base):
    __tablename__ = "admin_audit"

    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    target = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PlanGrant(Base):
    __tablename__ = "plan_grants"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    valid_until = Column(DateTime, nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class MonthlyUsage(Base):
    __tablename__ = "monthly_usage"
    __table_args__ = (UniqueConstraint("user_id", "period", "plan"),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    period = Column(String(7), nullable=False)
    plan = Column(String(10), nullable=False)
    used = Column(Integer, nullable=False, default=0)


class PlusRequest(Base):
    __tablename__ = "plus_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")
    price_vnd = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
