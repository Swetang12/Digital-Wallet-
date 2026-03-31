from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime

from db.session import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    sender_name = Column(String, nullable=False)
    receiver_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False)  # fund | pay
    created_at = Column(DateTime, default=datetime.utcnow)