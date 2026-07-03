import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import assets, auth, config, debts, expenses, finance, income, occupations, pension, profile, savings

app = FastAPI(title="Finance App API")

_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(finance.router, prefix="/api")
app.include_router(income.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(debts.router, prefix="/api")
app.include_router(savings.router, prefix="/api")
app.include_router(pension.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(occupations.router, prefix="/api")
app.include_router(profile.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
