import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.models.user import User, RoleEnum
from app.models.notification import Notification
from app.models.activity_log import ActivityLog
from app.models.driver import Driver
from app.database import get_db

from app.schemas.user import (
    UserCreate,
    UserOut,
    Token,
    SendOTPRequest,
    VerifyOTPRequest,
    ProfileUpdate,
    EmailUpdate,
    PasswordChange,
    UserRoleUpdate,
)

from app.utils.otp import generate_otp
from app.utils.email import send_email, send_otp_email
from app.utils.sms import send_sms
from app.crud.email_otp import save_otp, verify_otp

from app.crud.user import get_user_by_email, create_user, update_user
from app.crud.activity import record_activity
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user, require_roles

router = APIRouter()


def validate_password(password: str):
    pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$"

    if not re.match(pattern, password):
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must be at least 8 characters long and contain "
                "one uppercase letter, one lowercase letter, one number, "
                "and one special character."
            ),
        )


# ==========================
# SEND OTP
# ==========================

@router.post("/send-otp")
def send_otp(request: SendOTPRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, request.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=2)

    save_otp(db, request.email, otp, expires_at)
    delivered = send_otp_email(request.email, otp)
    if delivered:
        return {"message": "OTP sent successfully"}
    # Docker/local development has no SMTP credentials by default.  Expose a
    # one-time code only in this mode, while production keeps using email.
    return {"message": "Email is not configured; use the development OTP shown below.", "development_otp": otp}


# ==========================
# VERIFY OTP
# ==========================

@router.post("/verify-otp")
def verify_email_otp(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    if verify_otp(db, request.email, request.otp):
        return {
            "message": "OTP verified successfully"
        }

    raise HTTPException(
        status_code=400,
        detail="Invalid or expired OTP",
    )


# ==========================
# SIGNUP
# ==========================

@router.post("/signup", response_model=UserOut)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    validate_password(user_in.password)

    if get_user_by_email(db, user_in.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    user = create_user(
        db,
        user_in.email,
        user_in.password,
        user_in.full_name,
        user_in.phone,
        user_in.role,
    )

    # Keep account and driver records in sync so new Driver signups appear in
    # driver management and attendance immediately.
    if user.role == RoleEnum.Driver:
        db.add(Driver(
            user_id=user.user_id,
            name=user.full_name,
            phone=user.phone or "Not provided",
            license_number=f"PENDING-{str(user.user_id)[:8]}",
            status="Available",
        ))

    notification = Notification(
        user_id=user.user_id,
        title="Welcome",
        message="Your account has been created successfully.",
    )

    db.add(notification)
    db.commit()

    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/role", response_model=UserOut)
def change_user_role(user_id: str, data: UserRoleUpdate, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.user_id == current_user.user_id and data.role != RoleEnum.Admin:
        raise HTTPException(status_code=400, detail="You cannot remove your own Admin role")
    previous_role = user.role.value
    updated = update_user(db, user, role=data.role)
    if data.role == RoleEnum.Driver and not db.query(Driver).filter(Driver.user_id == user.user_id).first():
        db.add(Driver(user_id=user.user_id, name=user.full_name, phone=user.phone or "Not provided", license_number=f"PENDING-{str(user.user_id)[:8]}", status="Available"))
    record_activity(db, current_user.user_id, "user.role_updated", "user", user.user_id)
    role_message = f"Your FleetFlow role was changed from {previous_role} to {updated.role.value} by an administrator."
    db.add(Notification(user_id=updated.user_id, title="Role updated", message=role_message, type="account"))
    db.commit()
    # External delivery must not undo a completed administrative role change.
    send_email(updated.email, "FleetFlow role updated", f"Hello {updated.full_name},\n\n{role_message}\n\nRegards,\nFleetFlow Team")
    send_sms(updated.phone, role_message)
    return updated


@router.delete("/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), current_user=Depends(require_roles("Admin"))):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.delete(user)
    record_activity(db, current_user.user_id, "user.deleted", "user", user_id)
    db.commit()
    return {"message": "User deleted successfully"}


# ==========================
# LOGIN
# ==========================

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    print("\n" + "=" * 60)
    print("LOGIN REQUEST")
    print("=" * 60)

    try:
        user = get_user_by_email(db, form_data.username)
    except OperationalError as error:
        raise HTTPException(status_code=503, detail="Database unavailable. Start PostgreSQL and check DATABASE_URL.") from error

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
        }
    )

    db.add(ActivityLog(user_id=user.user_id, action="login", entity_type="user", entity_id=str(user.user_id)))
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ==========================
# CURRENT USER
# ==========================

@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_profile(
    profile: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_user(db, current_user, **profile.model_dump(exclude_unset=True))


@router.patch("/me/email", response_model=UserOut)
def update_email(
    request: EmailUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing_user = get_user_by_email(db, request.email)
    if existing_user and existing_user.user_id != current_user.user_id:
        raise HTTPException(status_code=400, detail="Email already registered")
    return update_user(db, current_user, email=request.email)


@router.patch("/me/password")
def change_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    validate_password(request.new_password)
    update_user(db, current_user, password=hash_password(request.new_password))
    return {"message": "Password updated successfully"}
