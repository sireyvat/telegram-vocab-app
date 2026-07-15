"""
config.py
---------
This file keeps all the "settings" of our app in ONE place.
(Khmer: ឯកសារនេះផ្ទុកការកំណត់សំខាន់ៗទាំងអស់របស់កម្មវិធីនៅកន្លែងតែមួយ)

Why this matters:
- We never hard-code secrets (like passwords or bot tokens) directly in our logic files.
- We read them from environment variables so the same code works in development
  and in production just by changing the .env file.
"""

import os
from dotenv import load_dotenv

# Load variables from a local .env file (if it exists) into the environment
load_dotenv()

class Settings:
    # Path to our SQLite database file. For production you could swap this
    # to a PostgreSQL URL later without changing any other code.
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vocab_app.db")

    # Telegram bot token, used later to verify that requests really come
    # from Telegram (see app/security.py in Step 5 of the roadmap).
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "REPLACE_ME")

    # A simple secret password for the teacher's Admin Dashboard (MVP only).
    # Later, replace with proper hashed-password login.
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "change-this-secret")

    # Used to sign JWT tokens issued to students after Telegram login.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-jwt-secret")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # token valid for 7 days


settings = Settings()
