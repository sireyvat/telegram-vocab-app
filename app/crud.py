"""
crud.py
-------
"CRUD" = Create, Read, Update, Delete.
This file holds small, reusable functions that talk directly to the
database, so our route files (routers/*.py) stay clean and readable.

(Khmer: ឯកសារនេះផ្ទុកមុខងារជាមូលដ្ឋានសម្រាប់ បង្កើត អាន កែប្រែ លុប ទិន្នន័យ)
"""

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from app import models, schemas


# ---------- Students ----------
def get_or_create_student(db: Session, telegram_id: str, username: str | None, first_name: str | None) -> models.Student:
    """
    Look up a student by their Telegram ID. If they've never opened the
    Mini App before, create a new row for them automatically.
    This is how we avoid a separate "sign up" step for students.
    """
    student = db.query(models.Student).filter(models.Student.telegram_id == telegram_id).first()
    if student is None:
        student = models.Student(telegram_id=telegram_id, username=username, first_name=first_name)
        db.add(student)
        db.commit()
        db.refresh(student)
    return student


# ---------- Lessons & Words (Admin) ----------
def create_lesson(db: Session, lesson_in: schemas.LessonCreate) -> models.Lesson:
    lesson = models.Lesson(
        title=lesson_in.title,
        lesson_date=lesson_in.lesson_date or date.today(),
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def add_word_to_lesson(db: Session, lesson_id: int, word_in: schemas.WordCreate) -> models.Word:
    word = models.Word(lesson_id=lesson_id, **word_in.model_dump())
    db.add(word)
    db.commit()
    db.refresh(word)
    return word


def list_lessons(db: Session):
    return db.query(models.Lesson).order_by(models.Lesson.lesson_date.desc()).all()


# ---------- Progress (SRS) ----------
def get_or_create_progress(db: Session, student_id: int, word_id: int) -> models.Progress:
    """
    Every (student, word) pair needs exactly one Progress row.
    A brand-new word is "due immediately" (next_review_date = today)
    so it shows up the first time the student opens a review session.
    """
    progress = (
        db.query(models.Progress)
        .filter(models.Progress.student_id == student_id, models.Progress.word_id == word_id)
        .first()
    )
    if progress is None:
        progress = models.Progress(student_id=student_id, word_id=word_id, next_review_date=date.today())
        db.add(progress)
        db.commit()
        db.refresh(progress)
    return progress


def get_due_words_for_student(db: Session, student_id: int, limit: int = 10):
    """
    Core "what should the student review right now?" query.

    Priority order:
      1. Words already tracked for this student that are DUE (next_review_date <= today),
         hardest / most-overdue first.
      2. If not enough due words, fill up with brand-new words the student hasn't seen yet.
    """
    today = date.today()

    due_progress = (
        db.query(models.Progress)
        .filter(models.Progress.student_id == student_id, models.Progress.next_review_date <= today)
        .order_by(models.Progress.next_review_date.asc(), models.Progress.ease_factor.asc())
        .limit(limit)
        .all()
    )
    due_words = [p.word for p in due_progress]

    if len(due_words) < limit:
        seen_word_ids = db.query(models.Progress.word_id).filter(models.Progress.student_id == student_id)
        new_words = (
            db.query(models.Word)
            .filter(~models.Word.id.in_(seen_word_ids))
            .order_by(models.Word.created_at.asc())
            .limit(limit - len(due_words))
            .all()
        )
        due_words.extend(new_words)

    return due_words


# ---------- Leaderboard ----------
def get_leaderboard(db: Session, limit: int = 10):
    """
    Top students by XP, for the class leaderboard.
    (Khmer: តារាងចំណាត់ថ្នាក់សិស្សតាម XP)
    """
    students = (
        db.query(models.Student)
        .order_by(models.Student.xp.desc())
        .limit(limit)
        .all()
    )
    return [
        schemas.LeaderboardEntryOut(
            rank=i + 1,
            first_name=s.first_name or "Student",
            xp=s.xp,
            current_streak=s.current_streak,
        )
        for i, s in enumerate(students)
    ]


# ---------- Analytics (Teacher) ----------
def get_hardest_words(db: Session, limit: int = 20):
    """
    Aggregate every logged Attempt to find which words the WHOLE CLASS
    struggles with the most. Sorted by error rate, highest first.
    """
    rows = (
        db.query(
            models.Word.id,
            models.Word.term,
            func.count(models.Attempt.id).label("total_attempts"),
            func.sum(func.cast(models.Attempt.is_correct == False, type_=Integer)).label("incorrect_count"),
        )
        .join(models.Attempt, models.Attempt.word_id == models.Word.id)
        .group_by(models.Word.id)
        .having(func.count(models.Attempt.id) > 0)
        .all()
    )

    results = []
    for word_id, term, total, incorrect in rows:
        incorrect = incorrect or 0
        results.append(
            schemas.WordDifficultyOut(
                word_id=word_id,
                term=term,
                total_attempts=total,
                incorrect_count=incorrect,
                error_rate=round(incorrect / total, 2) if total else 0.0,
            )
        )

    results.sort(key=lambda r: r.error_rate, reverse=True)
    return results[:limit]
