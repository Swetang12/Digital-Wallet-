from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from typing import Optional
import re

from core.config import SECRET_KEY, ALGORITHM
from db.session import get_db
from models.user import User
from core.security import verify_password, hash_password

router = APIRouter(prefix="/users", tags=["Users"])
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")


# ------------------------------------------------
# GET LOGGED-IN USER FROM TOKEN
# ------------------------------------------------
def get_logged_in_user(token: str, db: Session) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ------------------------------------
# SET GREEN PIN (ONLY ONCE)
# ------------------------------------
@router.post("/set-green-pin")
def set_green_pin(
    green_pin: str,
    confirm_green_pin: str,
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    user = get_logged_in_user(token, db)

    if user.green_pin:
        raise HTTPException(
            status_code=400,
            detail="Green PIN already set"
        )

    if green_pin != confirm_green_pin:
        raise HTTPException(
            status_code=400,
            detail="Green PINs do not match"
        )

    if not re.fullmatch(r"\d{4}", green_pin):
        raise HTTPException(
            status_code=400,
            detail="Green PIN must be exactly 4 digits"
        )

    user.green_pin = hash_password(green_pin)
    db.commit()

    return {"message": "Green PIN set successfully"}


# ------------------------------------------------
# PHONE NUMBER VALIDATION
# ------------------------------------------------
def validate_phone_no(phone_no: str):
    """
    Rules:
    - Only digits
    - Length exactly 10
    - Starts with 9, 8, 7, or 6
    """
    if not re.fullmatch(r"[6-9][0-9]{9}", phone_no):
        raise HTTPException(
            status_code=400,
            detail="Phone number must be 10 digits and start with 9, 8, 7, or 6"
        )


# ------------------------------------------------
# VIEW PROFILE
# ------------------------------------------------
@router.get("/profile")
def view_profile(
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    user = get_logged_in_user(token, db)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone_no": user.phone_no,
        "created_at": user.created_at
    }


# ------------------------------------------------
# UPDATE PROFILE + CHANGE PASSWORD
# ------------------------------------------------
@router.put("/profile")
def update_profile(
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone_no: Optional[str] = None,
    old_password: Optional[str] = None,
    new_password: Optional[str] = None,
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    user = get_logged_in_user(token, db)

    # ---------- NAME ----------
    if name is not None:
        user.name = name

    # ---------- EMAIL ----------
    if email is not None:
        existing_email = db.query(User).filter(
            User.email == email,
            User.id != user.id
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already in use"
            )
        user.email = email

    # ---------- PHONE NUMBER ----------
    if phone_no is not None:
        validate_phone_no(phone_no)

        existing_phone = db.query(User).filter(
            User.phone_no == phone_no,
            User.id != user.id
        ).first()
        if existing_phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number already in use"
            )
        user.phone_no = phone_no

    # ---------- CHANGE PASSWORD ----------
    if old_password or new_password:
        if not old_password or not new_password:
            raise HTTPException(
                status_code=400,
                detail="Both old_password and new_password are required"
            )

        if not verify_password(old_password, user.password):
            raise HTTPException(
                status_code=400,
                detail="Old password is incorrect"
            )

        user.password = hash_password(new_password)

    db.commit()
    db.refresh(user)

    return {
        "message": "Profile updated successfully",
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone_no": user.phone_no,
        "created_at": user.created_at
    }