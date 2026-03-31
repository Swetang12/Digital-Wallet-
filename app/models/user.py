from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True,index=True, nullable=False)
    password = Column(String, nullable=False)
    green_pin = Column(String, nullable=True)
    name = Column(String, nullable=False)
    phone_no = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)