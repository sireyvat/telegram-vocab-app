"""
srs.py
------
This file contains the Spaced Repetition algorithm.
(Khmer: ឯកសារនេះមានតក្កវិជ្ជា Spaced Repetition ដែលជាស្នូលនៃកម្មវិធី)

We use a SIMPLIFIED version of the "SM-2" algorithm (the one made famous
by SuperMemo / Anki). The idea in plain English:

  - If a student answers CORRECTLY, we wait LONGER before showing that
    word again (interval grows).
  - If a student answers INCORRECTLY, we reset the interval to almost
    zero, so the word comes back very soon (tomorrow).
  - Words the student finds "easy" over time get spaced out further and
    further apart (this is how long-term memory retention works).

We deliberately keep this simple for the MVP: instead of a 0-5 quality
score (used in classic SM-2), we just use correct/incorrect (0 or 1),
which is enough for multiple-choice / fill-in-the-blank quizzes.
"""

from datetime import date, timedelta

from app.models import Progress


def update_progress_after_answer(progress: Progress, is_correct: bool) -> Progress:
    """
    Given a student's current Progress row for one word, update it based
    on whether they just answered correctly or not.

    This function MUTATES and RETURNS the same `progress` object;
    the caller is responsible for committing it to the database.
    """

    if is_correct:
        progress.correct_count += 1
        progress.repetitions += 1

        # --- Grow the interval ---
        # First correct answer: review again tomorrow.
        # Second correct answer: review in ~3 days.
        # After that: multiply the previous interval by the ease factor.
        if progress.repetitions == 1:
            progress.interval_days = 1
        elif progress.repetitions == 2:
            progress.interval_days = 3
        else:
            progress.interval_days = round(progress.interval_days * progress.ease_factor)

        # Slightly increase ease factor (word is getting easier), capped at 3.0
        # so intervals don't explode too fast.
        progress.ease_factor = min(progress.ease_factor + 0.1, 3.0)

    else:
        progress.incorrect_count += 1
        # Wrong answer -> forget "progress", bring the word back almost immediately.
        progress.repetitions = 0
        progress.interval_days = 1  # review again tomorrow, not "in weeks"

        # Lower ease factor (word is harder than we thought), floor at 1.3
        # (1.3 is the standard SM-2 minimum so intervals never shrink to zero).
        progress.ease_factor = max(progress.ease_factor - 0.2, 1.3)

    progress.last_result_correct = is_correct
    progress.next_review_date = date.today() + timedelta(days=progress.interval_days)

    return progress


# Quality levels for self-rated flashcards (like Anki's 4 review buttons)
QUALITY_AGAIN = 0   # ភ្លេច — forgot completely
QUALITY_HARD = 1    # ពិបាក — remembered, but it was a struggle
QUALITY_GOOD = 2    # មធ្យម — remembered correctly with normal effort
QUALITY_EASY = 3    # ងាយ — remembered instantly, too easy


def update_progress_self_rated(progress: Progress, quality: int) -> Progress:
    """
    A richer alternative to update_progress_after_answer(), used by the
    self-rated flashcard mode where the student judges their OWN recall
    quality (Again / Hard / Good / Easy) instead of just right/wrong.

    (Khmer: នេះជាកំណែពង្រីកនៃ SRS algorithm ដែលប្រើនៅពេលសិស្សវាយតម្លៃខ្លួនឯង
    ជំនួសការឆ្លើយសំណួរពហុជម្រើសធម្មតា — ផ្តល់ភាពត្រឹមត្រូវខ្ពស់ជាងចំពោះការគណនា
    ថាតើគួររំលឹកពាក្យនេះនៅពេលណា)

    This mirrors Anki's default 4-button review, which is a well-tested
    refinement of the plain SM-2 algorithm.
    """
    is_correct = quality > QUALITY_AGAIN

    if quality == QUALITY_AGAIN:
        progress.incorrect_count += 1
        progress.repetitions = 0
        progress.interval_days = 1
        progress.ease_factor = max(progress.ease_factor - 0.2, 1.3)

    else:
        progress.correct_count += 1
        progress.repetitions += 1

        # Same base growth curve as the binary version: 1 day -> 3 days -> ease-based growth
        if progress.repetitions == 1:
            base_interval = 1
        elif progress.repetitions == 2:
            base_interval = 3
        else:
            base_interval = round(progress.interval_days * progress.ease_factor)

        if quality == QUALITY_HARD:
            # Remembered, but it was effortful -> grow the interval more cautiously
            progress.interval_days = max(1, round(base_interval * 0.8))
            progress.ease_factor = max(progress.ease_factor - 0.15, 1.3)

        elif quality == QUALITY_GOOD:
            # Normal recall -> use the standard growth curve as-is
            progress.interval_days = max(1, base_interval)

        elif quality == QUALITY_EASY:
            # Too easy -> push the next review out further, word is well-learned
            progress.interval_days = max(1, round(base_interval * 1.3))
            progress.ease_factor = min(progress.ease_factor + 0.15, 3.0)

    progress.last_result_correct = is_correct
    progress.next_review_date = date.today() + timedelta(days=progress.interval_days)

    return progress


def calculate_streak(last_practice_date, current_streak: int) -> tuple[int, bool]:
    """
    Decide the student's new streak count based on when they last practiced.

    Rules (simple daily-habit streak, like Duolingo):
      - Practiced today already       -> streak unchanged
      - Practiced yesterday           -> streak + 1 (habit continues)
      - Missed a day (or first time)  -> streak resets to 1

    Returns (new_streak, is_new_practice_day)
    """
    today = date.today()

    if last_practice_date == today:
        return current_streak, False  # already counted today, no change

    if last_practice_date == today - timedelta(days=1):
        return current_streak + 1, True  # kept the habit going

    return 1, True  # streak broken (or brand new student) -> restart at 1
