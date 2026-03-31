from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from core.config import SECRET_KEY, ALGORITHM
from db.session import get_db
from models.wallet import Wallet
from models.user import User
from models.transaction import Transaction
from schemas.wallet import AddMoney

router = APIRouter(prefix="/wallet", tags=["Wallet"])
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_user_id(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@router.get("/balance")
def get_balance(
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(token)
    wallet = db.query(Wallet).filter(Wallet.id == user_id).first()

    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {"balance": wallet.balance}


@router.post("/add-money")
def add_money(
    data: AddMoney,
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(token)
    user = db.query(User).filter(User.id == user_id).first()
    wallet = db.query(Wallet).filter(Wallet.id == user_id).first()
    
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    if not user or not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    wallet.balance += data.amount

    # FUND transaction
    tx = Transaction(
        sender_name="bank",
        receiver_name=user.name,
        amount=data.amount,
        type="fund"
    )

    db.add(tx)
    db.commit()

    return {
        "message": "Money added successfully",
        "balance": wallet.balance
    }