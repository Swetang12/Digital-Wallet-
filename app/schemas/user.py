from pydantic import BaseModel

class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    phone_no: str

class UserLogin(BaseModel):
    email: str
    password: str