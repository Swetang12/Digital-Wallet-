from fastapi import FastAPI

from db.session import Base, engine
from api.routes import auth, wallet, transactions, users, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital Wallet Backend")

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(transactions.router)
app.include_router(users.router)
app.include_router(admin.router)