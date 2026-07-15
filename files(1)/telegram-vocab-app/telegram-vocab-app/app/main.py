"""
main.py
-------
The entry point of our FastAPI application.
Run it with:  uvicorn app.main:app --reload

(Khmer: នេះជាចំណុចចាប់ផ្តើមកម្មវិធី FastAPI របស់យើង)

What happens here:
1. We create the FastAPI app.
2. We create all database tables automatically on startup (fine for SQLite MVP;
   once you have real student data, switch to a migration tool like Alembic
   so you don't accidentally wipe/alter data -- see README Step 7).
3. We "plug in" our two route files (routers) : admin.py and student.py.
4. We enable CORS so the Telegram Mini App (served from Telegram's domain)
   is allowed to call our API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import admin, student

# Create every table defined in models.py, if it doesn't already exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Vocab SRS - Telegram Mini App API",
    description="Backend for spaced-repetition vocabulary practice.",
    version="0.1.0",
)

# Allow the Mini App frontend (and local dev tools) to call this API.
# In production, replace "*" with your actual frontend domain for safety.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register our two sets of routes.
app.include_router(admin.router)
app.include_router(student.router)


@app.get("/", tags=["Health"])
def health_check():
    """Simple endpoint to confirm the API is alive. Visit / in your browser."""
    return {"status": "ok", "message": "Vocab SRS API is running"}
