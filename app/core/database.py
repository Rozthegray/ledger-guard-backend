from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# 1. Determine if we are using SQLite or Postgres
connect_args = {}

# SQLite specific argument (Render/Postgres will crash if this is present)
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

# 2. Create the engine with the correct arguments
engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True,
    connect_args=connect_args  # Only applies if using SQLite
)

# Create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your models
Base = declarative_base()

# Dependency for FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
