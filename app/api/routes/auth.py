from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from db.session import get_db
from models.user import User
from models.wallet import Wallet
from core.security import (
    hash_password,
    verify_password,
    create_access_token
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# -------------------------------
# REGISTER (email + password)
# -------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    email: str,
    password: str,
    name: str,
    phone_no: str,
    db: Session = Depends(get_db)
):
    
    if phone_no:
        # Validate phone number format
        if not phone_no.isdigit() or len(phone_no) != 10 or phone_no[0] not in "9876":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number must be 10 digits and start with 9, 8, 7, or 6"
            )

    # Check existing user
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )

    # Create user
    user = User(
        email=email,
        password=hash_password(password),
        name=name,
        phone_no=phone_no
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create wallet (1 wallet per user)
    wallet = Wallet(
        id=user.id,
        name=user.name,
        balance=0.0
    )
    db.add(wallet)
    db.commit()

    return {"message": "User registered successfully"}


# -------------------------------
# LOGIN (OAuth2 – Swagger Authorize)
# username = email
# password = password
# -------------------------------
@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    IMPORTANT:
    - Swagger sends: username + password
    - We treat username as EMAIL
    """

    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={"user_id": user.id}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }