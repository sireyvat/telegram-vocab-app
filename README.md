# Vocab SRS — Telegram Mini App for Vocabulary Retention

A spaced-repetition + retrieval-practice tool students open inside Telegram
before each new class, so what they learned last lesson actually sticks.

## 1. Project folder structure

```
telegram-vocab-app/
├── app/
│   ├── main.py            # FastAPI app entry point, wires everything together
│   ├── config.py          # Settings loaded from environment variables
│   ├── database.py        # SQLAlchemy engine/session setup
│   ├── models.py          # DATABASE SCHEMA (tables)
│   ├── schemas.py         # API request/response shapes (Pydantic)
│   ├── crud.py            # Reusable database query functions
│   ├── srs.py             # Spaced repetition (SM-2 style) algorithm
│   └── routers/
│       ├── admin.py       # Teacher endpoints (lessons, words, analytics)
│       └── student.py     # Student endpoints (login, review, answer)
├── frontend_demo/
│   └── index.html         # Minimal Telegram Mini App demo (flashcard + quiz)
├── requirements.txt
├── .env.example
└── README.md
```

**Khmer summary (សង្ខេបជាភាសាខ្មែរ):** `models.py` គឺជារចនាសម្ព័ន្ធតារាងទិន្នន័យ
(schema), `srs.py` គឺជាតក្កវិជ្ជា Spaced Repetition, `routers/admin.py`
សម្រាប់គ្រូបញ្ចូលពាក្យ ហើយ `routers/student.py` សម្រាប់សិស្សរៀន និងធ្វើតេស្ត។

---

## 2. Database schema (the core design decision)

| Table      | Purpose |
|------------|---------|
| `students` | One row per Telegram user. Stores `xp`, `current_streak`, `longest_streak`. |
| `lessons`  | Groups words by class/date (e.g. "Unit 3: Travel", 2026-07-10). |
| `words`    | `term`, `meaning`, `example_sentence`, `distractors` (for multiple choice). |
| `progress` | **The SRS engine.** One row per `(student, word)` pair: `ease_factor`, `interval_days`, `next_review_date`. |
| `attempts` | Permanent log of every answer (correct/incorrect). Powers teacher analytics. |

Why split `progress` from `attempts`?
- `progress` = **current state** ("when should this student see this word again?") — gets updated in place.
- `attempts` = **historical log** ("every answer ever given") — never modified, only appended to. This is what lets you later ask "which word does the whole class struggle with?"

**Khmer:** តារាង `progress` ចងចាំស្ថានភាពបច្ចុប្បន្នរបស់ពាក្យនីមួយៗសម្រាប់សិស្សម្នាក់ៗ
(សម្រាប់សម្រេចថាតើគួររំលឹកនៅពេលណា) ចំណែក `attempts` ចងចាំប្រវត្តិចម្លើយទាំងអស់
ជាអចិន្ត្រៃយ៍ សម្រាប់វិភាគជាក្រុម។

---

## 3. The Spaced Repetition algorithm (`app/srs.py`)

We use a simplified **SM-2** algorithm (same family as Anki):

- **Correct answer** → interval grows (1 day → 3 days → interval × ease_factor), ease_factor increases slightly.
- **Wrong answer** → interval resets to 1 day (review again tomorrow), ease_factor decreases (word is marked "harder").
- New words are due immediately, so they show up the first time a student opens a review session.

This is intentionally simple (correct/incorrect only, not SM-2's 0-5 quality
scale) because multiple-choice and fill-in-the-blank quizzes naturally give
you binary feedback. You can upgrade to a full 0-5 scale later if you add
self-graded flashcards ("How well did you know this? 1-5").

---

## 4. Boilerplate: how the FastAPI app connects to the database

Already built and tested in this project — see `app/database.py` + `app/main.py`.
Key idea:

```python
# database.py
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

```python
# main.py
Base.metadata.create_all(bind=engine)   # creates tables on startup
app.include_router(admin.router)
app.include_router(student.router)
```

Every route then just declares `db: Session = Depends(get_db)` and FastAPI
handles opening/closing the connection automatically.

I ran a full simulated flow locally (create lesson → add word → student
login → get review session → submit answer → check analytics) to confirm
everything works end-to-end before handing this to you.

---

## 5. How to run it right now

```bash
cd telegram-vocab-app
pip install -r requirements.txt
cp .env.example .env          # then edit .env with your real secrets
uvicorn app.main:app --reload
```

Open **http://localhost:8000/docs** — FastAPI auto-generates an interactive
Swagger UI where you can test every endpoint (create a lesson, add words,
simulate a student) without writing any frontend code yet.

To try the demo frontend: just open `frontend_demo/index.html` in a browser
(it works standalone outside Telegram too, using a fake test user ID).

---

## 6. Step-by-step development roadmap

**Phase 1 — Backend foundation (✅ done in this deliverable)**
1. Folder structure, database schema, SRS algorithm, admin + student API routes.
2. Test locally via `/docs` — create a lesson, add 5-10 real words, simulate answers.

**Phase 2 — Telegram integration**
3. Create your bot with [@BotFather](https://t.me/BotFather), get a bot token, register your Mini App URL (`/newapp`).
4. Deploy the FastAPI backend somewhere with HTTPS (Telegram requires it) — e.g. Railway, Render, or a VPS + Caddy/Nginx.
5. **Security upgrade:** replace the "trust telegram_id" shortcut in `routers/student.py` with real verification of Telegram's `initData` signature (HMAC using your bot token), so students can't fake another student's ID. This is a must-do before real classroom use.

**Phase 3 — Real frontend**
6. Build the full Mini App UI (Tailwind CSS) beyond the demo: flashcard flip animation, fill-in-the-blank input, streak/XP progress bar, "session complete" celebration screen. Host it as static files (Vercel/Netlify/Cloudflare Pages) or serve it directly from FastAPI's `StaticFiles`.

**Phase 4 — Admin Dashboard**
7. Build a simple teacher web page (can even be a separate small React/HTML page, not inside Telegram) to add lessons/words through a form instead of raw API calls. Add proper login (replace the shared `X-Admin-Key` with hashed-password auth) once more than one teacher uses it.

**Phase 5 — Data & reliability**
8. Switch from `Base.metadata.create_all()` to **Alembic migrations** once you have real student data, so schema changes don't risk data loss.
9. Move from SQLite to PostgreSQL if you expect concurrent write load from many students at once (SQLite is fine for an MVP / single classroom).
10. Add scheduled reminders: a small cron job or Telegram Bot API push that messages students whose `next_review_date` is today ("You have 5 words due for review!").

**Phase 6 — Analytics for you**
11. Expand `/admin/analytics/hardest-words` into a small dashboard: error rate per lesson, per student engagement (streak distribution), words that are "stuck" (never graduate past `repetitions=0`).

---

## 7. Quick API reference

| Method | Path | Who | Purpose |
|---|---|---|---|
| POST | `/admin/lessons` | Teacher | Create a lesson |
| GET | `/admin/lessons` | Teacher | List lessons + words |
| POST | `/admin/lessons/{id}/words` | Teacher | Add a word to a lesson |
| GET | `/admin/analytics/hardest-words` | Teacher | See which words the class struggles with |
| POST | `/student/login` | Student | Auto-register/fetch student by Telegram ID |
| GET | `/student/review-session` | Student | Get today's due + new words |
| POST | `/student/answer` | Student | Submit an answer, updates SRS + XP + streak |

All admin routes require header `X-Admin-Key: <your ADMIN_SECRET_KEY>`.
