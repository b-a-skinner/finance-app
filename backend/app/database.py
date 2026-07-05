import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

url = os.getenv("DATABASE_URL", "sqlite:///./finance.db")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+pg8000://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+pg8000://", 1)

connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
