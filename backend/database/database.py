from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# Project root:
# D:\smart-ev-charging
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# SQLite database file:
# D:\smart-ev-charging\data\smart_ev.db
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_FILE = DATABASE_DIR / "smart_ev.db"


# SQLite connection URL
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


# Database session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# Base class for database models
Base = declarative_base()


def get_db():
    """
    Provide a database session for FastAPI routes.

    The session is automatically closed after the request.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()