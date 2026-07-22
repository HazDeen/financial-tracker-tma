# backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.endpoints import statements, analytics, shifts, debts, recurring, ai_advisor, actions, transactions, users

api_router = APIRouter()

api_router.include_router(statements.router, prefix="/statements", tags=["Statements & Parsing"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Reports"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["Work Shifts & Salary"])
api_router.include_router(debts.router, prefix="/debts", tags=["Credits & Debts"])
api_router.include_router(recurring.router, prefix="/recurring", tags=["Recurring Payments"])
api_router.include_router(ai_advisor.router, prefix="/ai-advisor", tags=["AI Advisor (Gemini)"])
api_router.include_router(actions.router, prefix="/actions", tags=["actions"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Manual Transactions"])
api_router.include_router(users.router, prefix="/users", tags=["Users & Authentication"])