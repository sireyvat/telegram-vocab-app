"""
models.py
---------
This file defines the DATABASE SCHEMA: every table in our database,
as a Python class. SQLAlchemy turns these classes into real SQL tables.

(Khmer: ឯកសារនេះកំណត់រចនាសម្ព័ន្ធតារាងទិន្នន័យទាំងអស់)

Tables in this MVP:
1. Student   -> one row per Telegram user (student)
2. Lesson    -> groups words by class/date (e.g. "Lesson 5 - 2026-07-10")
3. Word      -> vocabulary items (term, meaning, example sentence)
4. Progress  -> SRS (Spaced Repetition) state per student PER word
5. Attempt   -> a permanent log of every quiz answer, for teacher analytics
"""

from datetime import datetime, date

from sqlalchemy import (
    Column, Integer, String, Text, Float, Date, DateTime,
    ForeignKey, Boolean, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


class Student(Base):
    """One row = one student who has opened the Mini App via Telegram."""
    __tablename__ = "vocab_students"

    id = Column(Integer, primary_key=True, index=True)

    # Telegram gives every user a unique numeric ID -- this is how we
    # recognize returning students without asking them to make an account.
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)

    # --- Gamification fields ---
    xp = Column(Integer, default=0)                 # total experience points
    current_streak = Column(Integer, default=0)     # consecutive days practiced
    longest_streak = Column(Integer, default=0)
    last_practice_date = Column(Date, nullable=True)  # used to calculate streaks

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships: lets us write `student.progress` or `student.attempts` in code
    progress = relationship("Progress", back_populates="student", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="student", cascade="all, delete-orphan")


class Lesson(Base):
    """
    Groups vocabulary by class session, so the teacher can tag words
    ("these 10 words belong to Lesson 5, taught on 2026-07-10").
    """
    __tablename__ = "vocab_lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)          # e.g. "Unit 3: Travel"
    lesson_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    words = relationship("Word", back_populates="lesson", cascade="all, delete-orphan")


class Word(Base):
    """A single vocabulary item entered by the teacher."""
    __tablename__ = "vocab_words"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("vocab_lessons.id"), nullable=False)

    term = Column(String, nullable=False, index=True)     # the word itself
    meaning = Column(String, nullable=False)               # definition / translation
    example_sentence = Column(Text, nullable=True)
    # Optional: distractors (wrong choices) for multiple-choice quizzes.
    # Stored as a comma-separated string for MVP simplicity; could become
    # its own table later if you want smarter distractor generation.
    distractors = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    lesson = relationship("Lesson", back_populates="words")
    progress_entries = relationship("Progress", back_populates="word", cascade="all, delete-orphan")
    attempts = relationship("Attempt", back_populates="word", cascade="all, delete-orphan")


class Progress(Base):
    """
    THE HEART OF THE SRS SYSTEM.
    One row = the current spaced-repetition state of ONE word for ONE student.

    (Khmer: តារាងនេះជាស្នូលនៃប្រព័ន្ធ Spaced Repetition
    វារក្សាទុកថាសិស្សម្នាក់ៗចាំពាក្យនីមួយៗបានល្អកម្រិតណា)

    We use a simplified SM-2 algorithm (the same family of algorithm used
    by Anki). See app/srs.py for the logic that updates these fields.
    """
    __tablename__ = "vocab_progress"
    __table_args__ = (UniqueConstraint("student_id", "word_id", name="uq_student_word"),)

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("vocab_students.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("vocab_words.id"), nullable=False)

    # --- SM-2 style SRS fields ---
    ease_factor = Column(Float, default=2.5)     # how "easy" this word is for this student
    interval_days = Column(Integer, default=0)   # days to wait until next review
    repetitions = Column(Integer, default=0)     # consecutive correct answers
    next_review_date = Column(Date, default=date.today)

    # --- Extra stats used to flag "difficult words" for the teacher ---
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    last_result_correct = Column(Boolean, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="progress")
    word = relationship("Word", back_populates="progress_entries")


class Attempt(Base):
    """
    A permanent log of EVERY answer a student gives.
    This is what powers the teacher's analytics dashboard
    ("which words are hardest for the class overall?").
    """
    __tablename__ = "vocab_attempts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("vocab_students.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("vocab_words.id"), nullable=False)

    question_type = Column(String, nullable=False)   # "flashcard" | "multiple_choice" | "fill_blank"
    is_correct = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=True)  # optional: how long they took
    answered_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="attempts")
    word = relationship("Word", back_populates="attempts")
