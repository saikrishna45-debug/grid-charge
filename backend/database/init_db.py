from backend.database.database import Base, engine

# Import models so SQLAlchemy knows about all database tables.
from backend.database import models  # noqa: F401


def initialize_database():
    """
    Create all database tables if they do not already exist.
    """

    Base.metadata.create_all(bind=engine)

    print("DATABASE INITIALIZED SUCCESSFULLY")
    print(f"Database location: {engine.url.database}")


if __name__ == "__main__":
    initialize_database()