"""
schemas.py
----------
These are "Pydantic" models. Do not confuse them with models.py!

- models.py   -> describes the DATABASE tables (SQLAlchemy)
- schemas.py  -> describes the JSON shape going IN and OUT of our API (Pydantic)

(Khmer: models.py សម្រាប់មូលដ្ឋានទិន្នន័យ ចំណែក schemas.py សម្រាប់ទម្រង់ JSON
ដែលចូល-ចេញពី API)

Why separate them? Because we usually don't want to expose every database
column to the outside world (e.g. we may hide internal IDs), and we want to
validate incoming data BEFORE it touches the database.
"""

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


# ---------- Word ----------
class WordCreate(BaseModel):
    """Shape of data the teacher sends when adding a new word."""
    term: str
    meaning: str
    example_sentence: Optional[str] = None
    distractors: Optional[str] = None   # comma-separated wrong options


class WordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # lets us build this from an ORM object

    id: int
    term: str
    meaning: str
    example_sentence: Optional[str] = None
    lesson_id: int


# ---------- Lesson ----------
class LessonCreate(BaseModel):
    title: str
    lesson_date: Optional[date] = None


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    lesson_date: date
    words: List[WordOut] = []


# ---------- Student ----------
class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: str
    first_name: Optional[str]
    xp: int
    current_streak: int
    longest_streak: int


# ---------- Quiz / Practice flow ----------
class ReviewWordOut(BaseModel):
    """A word sent to the student for practice, with its due date info."""
    model_config = ConfigDict(from_attributes=True)

    word_id: int
    term: str
    meaning: str
    example_sentence: Optional[str] = None
    options: List[str] = []   # multiple-choice options (correct + distractors, shuffled)


class AnswerSubmit(BaseModel):
    """What the frontend sends after a student answers a question."""
    student_telegram_id: str
    word_id: int
    question_type: str          # "flashcard" | "multiple_choice" | "fill_blank"
    is_correct: bool
    response_time_ms: Optional[int] = None


class AnswerResult(BaseModel):
    """What we send back after grading an answer."""
    correct: bool
    xp_earned: int
    new_xp_total: int
    current_streak: int
    next_review_date: date


# ---------- Analytics (for the teacher) ----------
class WordDifficultyOut(BaseModel):
    word_id: int
    term: str
    total_attempts: int
    incorrect_count: int
    error_rate: float   # incorrect / total, easy way to sort "hardest words"
