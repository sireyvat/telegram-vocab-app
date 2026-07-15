"""
database.py
------------
This file connects our app to the database (SQLite for now).
(Khmer: ឯកសារនេះភ្ជាប់កម្មវិធីទៅមូលដ្ឋានទិន្នន័យ)

Think of it like this:
- `engine`   = the actual "road" that connects Python to the database file.
- `SessionLocal` = a "car" (a temporary connection) we create every time
  we need to talk to the database (read or write data).
- `Base`     = a blueprint class that all our tables (models.py) inherit from.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# `connect_args` is only needed for SQLite because, by default, SQLite only
# allows one thread to talk to it. FastAPI can use multiple threads, so we
# turn that restriction off here. (Not needed for PostgreSQL/MySQL later.)
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

# Every database "conversation" (a request) gets its own Session from this factory.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All ORM models (tables) in models.py will inherit from this Base class.
Base = declarative_base()


def get_db():
    """
    This is a FastAPI "dependency". FastAPI will call this function
    automatically for any route that needs database access.

    Khmer: មុខងារនេះបើកការតភ្ជាប់ទិន្នន័យសម្រាប់ 1 សំណើ (request) មួយ
    ហើយបិទវាវិញបន្ទាប់ពីរួចរាល់ ដើម្បីជៀសវាងការលេចធ្លាយធនធាន។
    """
    db = SessionLocal()
    try:
        yield db          # hand the session to the route function
    finally:
        db.close()         # always close it afterwards, even if an error happened
