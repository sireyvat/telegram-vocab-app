"""
routers/student.py
-------------------
Endpoints used by the STUDENT-facing Telegram Mini App
(flashcards, quizzes, streaks, XP).

(Khmer: endpoint ទាំងនេះសម្រាប់សិស្សប្រើនៅក្នុង Mini App)

NOTE on auth (MVP): for simplicity these routes trust the
`telegram_id` sent by the frontend. In Step 5 of the roadmap (README),
we upgrade this to verify Telegram's `initData` signature so a student
can't fake being someone else. Do that before going live.
"""

import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas, models, srs

router = APIRouter(prefix="/student", tags=["Student"])


@router.post("/login", response_model=schemas.StudentOut)
def login(telegram_id: str, username: str | None = None, first_name: str | None = None, db: Session = Depends(get_db)):
    """
    Called once when the Mini App opens.
    Telegram gives us the user's ID automatically (via window.Telegram.WebApp),
    so students never type a username/password -- this IS their login.
    """
    student = crud.get_or_create_student(db, telegram_id, username, first_name)
    return student


@router.get("/review-session", response_model=list[schemas.ReviewWordOut])
def get_review_session(telegram_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    Builds today's practice set for a student:
    a mix of DUE words (spaced repetition) and new words.
    Each word comes with shuffled multiple-choice options ready for the quiz UI.
    """
    student = db.query(models.Student).filter(models.Student.telegram_id == telegram_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found, call /student/login first")

    words = crud.get_due_words_for_student(db, student.id, limit=limit)

    session = []
    for word in words:
        distractors = [d.strip() for d in (word.distractors or "").split(",") if d.strip()]
        options = distractors[:3] + [word.meaning]
        random.shuffle(options)

        session.append(
            schemas.ReviewWordOut(
                word_id=word.id,
                term=word.term,
                meaning=word.meaning,
                example_sentence=word.example_sentence,
                options=options,
            )
        )
    return session


@router.post("/answer", response_model=schemas.AnswerResult)
def submit_answer(answer: schemas.AnswerSubmit, db: Session = Depends(get_db)):
    """
    Called every time a student answers a flashcard/quiz question.
    This single endpoint does THREE jobs:
      1. Logs the attempt (for teacher analytics)
      2. Updates the SRS progress for that word (so we know when to show it again)
      3. Updates the student's XP and daily streak (gamification)
    """
    student = db.query(models.Student).filter(models.Student.telegram_id == answer.student_telegram_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    word = db.query(models.Word).filter(models.Word.id == answer.word_id).first()
    if not word:
        raise HTTPException(status_code=404, detail="Word not found")

    # 1. Log the raw attempt -- this table is never modified, only appended to.
    attempt = models.Attempt(
        student_id=student.id,
        word_id=word.id,
        question_type=answer.question_type,
        is_correct=answer.is_correct,
        response_time_ms=answer.response_time_ms,
    )
    db.add(attempt)

    # 2. Update this student's SRS state for this specific word.
    #    Use the richer self-rated algorithm if the frontend sent a quality
    #    rating (flashcard mode); otherwise fall back to the simple
    #    correct/incorrect algorithm (quiz mode).
    progress = crud.get_or_create_progress(db, student.id, word.id)
    if answer.quality is not None:
        srs.update_progress_self_rated(progress, answer.quality)
    else:
        srs.update_progress_after_answer(progress, answer.is_correct)

    # 3. Gamification: XP + streak.
    #    Self-rated mode gives graded XP (Easy > Good > Hard > Again) so
    #    honest self-assessment feels rewarded, not punished.
    if answer.quality is not None:
        xp_by_quality = {0: 2, 1: 5, 2: 10, 3: 15}
        xp_earned = xp_by_quality.get(answer.quality, 5)
    else:
        xp_earned = 10 if answer.is_correct else 2  # small XP even for wrong answers = effort counts
    student.xp += xp_earned

    new_streak, is_new_day = srs.calculate_streak(student.last_practice_date, student.current_streak)
    student.current_streak = new_streak
    student.longest_streak = max(student.longest_streak, new_streak)
    if is_new_day:
        from datetime import date
        student.last_practice_date = date.today()

    db.commit()
    db.refresh(progress)
    db.refresh(student)

    return schemas.AnswerResult(
        correct=answer.is_correct,
        xp_earned=xp_earned,
        new_xp_total=student.xp,
        current_streak=student.current_streak,
        next_review_date=progress.next_review_date,
    )
