import uuid
import enum

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class RoleEnum(str, enum.Enum):
    Admin = "Admin"
    FleetManager = "FleetManager"
    Driver = "Driver"
    Dispatcher = "Dispatcher"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('Admin', 'FleetManager', 'Driver', 'Dispatcher')",
            name="users_role_check",
        ),
    )

    user_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    full_name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )

    password = Column(
        String(255),
        nullable=False
    )

    phone = Column(
        String(15)
    )

    address = Column(
        String(255),
        nullable=True
    )

    role = Column(
        Enum(RoleEnum),
        nullable=False,
        default=RoleEnum.Driver
    )

    # Email OTP verification
    email_verified = Column(
        Boolean,
        nullable=False,
        default=False
    )

    verification_code = Column(
        String(6),
        nullable=True
    )

    verification_code_expires_at = Column(
        DateTime,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
