from typing import Callable

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.crud.user import get_user_by_email
from app.core.security import SECRET_KEY, ALGORITHM
from app.models.driver import Driver
from app.models.trip import Trip


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        email = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    try:
        user = get_user_by_email(db, email)
    except OperationalError as error:
        raise HTTPException(status_code=503, detail="Database unavailable. Start PostgreSQL and check DATABASE_URL.") from error

    if user is None:
        raise credentials_exception

    return user


def require_roles(*allowed_roles: str) -> Callable:
    def role_checker(
        current_user=Depends(get_current_user)
    ):
        if current_user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action",
            )

        return current_user

    return role_checker


def get_current_driver(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role.value != "Driver":
        raise HTTPException(status_code=403, detail="This action is limited to drivers")
    driver = db.query(Driver).filter(Driver.user_id == current_user.user_id).first()
    if not driver:
        raise HTTPException(status_code=403, detail="No driver profile is assigned to this account")
    return driver


def can_access_trip(trip: Trip, current_user, db: Session) -> bool:
    if current_user.role.value != "Driver":
        return True
    driver = db.query(Driver).filter(Driver.user_id == current_user.user_id).first()
    return bool(driver and trip.driver_id == driver.driver_id)
