"""
ai_vocab.py
-----------
This file lets the teacher paste a paragraph (like the "Technology" reading
passage) and get back a ready-to-review list of vocabulary words, complete
with Khmer meanings, an example sentence, and quiz distractors -- instead of
typing all of that by hand for every word.

(Khmer: ឯកសារនេះអនុញ្ញាតឲ្យគ្រូបិទភ្ជាប់ paragraph ហើយ AI ជួយស្រង់ចេញពាក្យ
សំខាន់ៗ ព្រមទាំងន័យជាភាសាខ្មែរ ប្រយោគឧទាហរណ៍ និងជម្រើសខុសសម្រាប់ quiz)

Setup required: the teacher needs their own Anthropic API key from
https://console.anthropic.com (this is a separate, paid-per-use developer
account -- NOT the same login as claude.ai). Set it as the ANTHROPIC_API_KEY
environment variable in Render. Without it, this feature returns a clear
error telling the teacher what to do, but the rest of the app keeps working.
"""

import json
from anthropic import Anthropic

from app.config import settings
from app.schemas import GeneratedWordOut


SYSTEM_PROMPT = """You are a helpful assistant for a Khmer-speaking English teacher.
Given a paragraph of English text, pick the most useful vocabulary words for
intermediate English learners to study (words a student might not already know).

For EACH word, produce:
- term: the word exactly as it should be studied (base/dictionary form is fine)
- meaning: a short, natural Khmer translation/definition
- example_sentence: a sentence USING THE WORD, ideally adapted from the
  paragraph itself, so it matches the context the student just read
- distractors: exactly 3 plausible-but-wrong Khmer meanings, comma-separated
  (these are used as wrong answers in a multiple-choice quiz, so they should
  be different enough from the correct meaning to not be confusing, but
  still be real, relevant Khmer words)

Respond with ONLY a JSON array, no other text, no markdown code fences.
Example format:
[
  {"term": "Technology", "meaning": "បច្ចេកវិទ្យា", "example_sentence": "Technology has changed the way people live.", "distractors": "ប្រពៃណី, អារម្មណ៍, រូបិយវត្ថុ"}
]
"""


def generate_vocab_from_paragraph(paragraph: str, num_words: int = 10) -> list[GeneratedWordOut]:
    """
    Calls Claude to extract vocabulary words from a teacher's paragraph.
    Raises a ValueError with a friendly message if the API key is missing
    or the API call fails, so the route can turn that into a clean HTTP error.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError(
            "AI vocabulary generation is not set up yet. "
            "Add your ANTHROPIC_API_KEY in Render's Environment settings "
            "(get one at https://console.anthropic.com)."
        )

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = (
        f"Extract {num_words} vocabulary words from this paragraph:\n\n{paragraph}"
    )

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # The model's reply should be plain JSON text (per our system prompt).
    raw_text = "".join(block.text for block in response.content if block.type == "text")

    # Defensive cleanup in case the model wraps the JSON in ```json fences anyway.
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI response could not be read as JSON: {e}")

    return [GeneratedWordOut(**item) for item in parsed]
