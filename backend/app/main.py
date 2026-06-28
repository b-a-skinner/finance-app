from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, debts, expenses, finance, income, pension, savings

app = FastAPI(title="Finance App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(finance.router, prefix="/api")
app.include_router(income.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(debts.router, prefix="/api")
app.include_router(savings.router, prefix="/api")
app.include_router(pension.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
