from fastapi import FastAPI
from app.routes import events, transactions, reconciliation
from app.db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payment Service")

app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(reconciliation.router, prefix="/reconciliation", tags=["Reconciliation"])