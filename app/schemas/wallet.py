from pydantic import BaseModel

class AddMoney(BaseModel):
    amount: float