from pydantic import BaseModel

class SendMoney(BaseModel):
    receiver_email: str
    amount: float