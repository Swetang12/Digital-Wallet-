from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy import func

from core.config import SECRET_KEY, ALGORITHM, ADMIN_EMAIL
from db.session import get_db
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction

router = APIRouter(prefix="/admin", tags=["Admin"])
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")


# -------------------------
# ADMIN AUTH CHECK
# -------------------------
def get_admin(token: str, db: Session):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    admin = db.query(User).filter(User.id == user_id).first()
    if not admin or admin.email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin access required")

    return admin


# -------------------------
# GET ALL USERS
# -------------------------
@router.get("/users")
def get_all_users(
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    get_admin(token, db)

    users = db.query(User).all()
    return users


# -------------------------
# DELETE USER BY EMAIL
# -------------------------
@router.delete("/users")
def delete_user_by_email(
    email: str,
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    admin = get_admin(token, db)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email == admin.email:
        raise HTTPException(
            status_code=400,
            detail="Admin cannot delete own account"
        )

    # Delete transactions
    db.query(Transaction).filter(
        (Transaction.sender_name == user.name) |
        (Transaction.receiver_name == user.name)
    ).delete(synchronize_session=False)

    # Delete wallet
    wallet = db.query(Wallet).filter(Wallet.id == user.id).first()
    if wallet:
        db.delete(wallet)

    # Delete user
    db.delete(user)
    db.commit()

    return {"message": f"User '{email}' deleted successfully"}


# -------------------------
# TOTAL WALLET BALANCE
# -------------------------
@router.get("/total-wallet-balance")
def total_wallet_balance(
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    get_admin(token, db)
    total = db.query(func.sum(Wallet.balance)).scalar() or 0
    return {"total_wallet_balance": total}


# -------------------------
# ALL TRANSACTIONS
# -------------------------
@router.get("/transactions")
def all_transactions(
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    get_admin(token, db)
    return db.query(Transaction).order_by(Transaction.id.desc()).all()


# -------------------------
# TOP USERS (HIGH → LOW)
# -------------------------
@router.get("/top-users")
def top_users(
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    get_admin(token, db)

    users = (
        db.query(User.name, User.email, Wallet.balance)
        .join(Wallet, Wallet.id == User.id)
        .order_by(Wallet.balance.desc())
        .all()
    )

    return [
        {
            "name": u.name,
            "email": u.email,
            "balance": u.balance
        }
        for u in users
    ]