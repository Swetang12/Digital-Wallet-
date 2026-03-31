from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from datetime import datetime, date

from core.config import SECRET_KEY, ALGORITHM
from db.session import get_db
from models.user import User
from models.wallet import Wallet
from models.transaction import Transaction
from schemas.transaction import SendMoney
from core.security import verify_password

router = APIRouter(prefix="/transactions", tags=["Transactions"])
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")

DAILY_PAY_LIMIT = 100000  # ₹1,00,000 per day


# ------------------------------------------------
# GET USER ID FROM TOKEN
# ------------------------------------------------
def get_user_id(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ------------------------------------
# PAY MONEY (GREEN PIN REQUIRED)
# ------------------------------------
@router.post("/pay")
def pay_money(
    data: SendMoney,
    green_pin: str,
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    sender_id = get_user_id(token)

    sender = db.query(User).filter(User.id == sender_id).first()
    receiver = db.query(User).filter(User.email == data.receiver_email).first()

    if not sender or not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    if not sender.green_pin:
        raise HTTPException(
            status_code=400,
            detail="Green PIN not set. Please set Green PIN first."
        )

    if not verify_password(green_pin, sender.green_pin):
        raise HTTPException(
            status_code=400,
            detail="Invalid Green PIN"
        )

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    sender_wallet = db.query(Wallet).filter(Wallet.id == sender.id).first()
    receiver_wallet = db.query(Wallet).filter(Wallet.id == receiver.id).first()

    if sender_wallet.balance < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # -------- DAILY LIMIT CHECK --------
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    today_spent = (
        db.query(Transaction)
        .filter(
            Transaction.sender_name == sender.name,
            Transaction.type == "pay",
            Transaction.created_at >= today_start,
            Transaction.created_at <= today_end
        )
        .with_entities(Transaction.amount)
        .all()
    )

    total_spent_today = sum(t.amount for t in today_spent)
    remaining_limit = max(0, DAILY_PAY_LIMIT - total_spent_today)

    if data.amount > remaining_limit:
        raise HTTPException(
            status_code=400,
            detail=f"Daily limit exceeded. You can transfer only ₹{remaining_limit} today."
        )

    # -------- UPDATE BALANCES --------
    sender_wallet.balance -= data.amount
    receiver_wallet.balance += data.amount

    tx = Transaction(
        sender_name=sender.name,
        receiver_name=receiver.name,
        amount=data.amount,
        type="pay"
    )

    db.add(tx)
    db.commit()

    return {"message": "Payment successful"}


# ------------------------------------------------
# TRANSACTION HISTORY WITH FILTERS
# ------------------------------------------------
@router.get("/history")
def transaction_history(
    type: str = Query(None, description="fund or pay"),
    from_date: date = Query(None, description="YYYY-MM-DD"),
    to_date: date = Query(None, description="YYYY-MM-DD"),
    token: str = Depends(oauth2),
    db: Session = Depends(get_db)
):
    user_id = get_user_id(token)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    query = db.query(Transaction).filter(
        (Transaction.sender_name == user.name) |
        (Transaction.receiver_name == user.name)
    )

    if type:
        if type not in ["fund", "pay"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid type. Allowed values: fund, pay"
            )
        query = query.filter(Transaction.type == type)

    if from_date:
        query = query.filter(
            Transaction.created_at >= datetime.combine(
                from_date, datetime.min.time()
            )
        )

    if to_date:
        query = query.filter(
            Transaction.created_at <= datetime.combine(
                to_date, datetime.max.time()
            )
        )

    transactions = query.order_by(Transaction.created_at.desc()).all()
    return transactions