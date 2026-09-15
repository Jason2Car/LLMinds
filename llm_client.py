"""
Thin wrapper around the OpenAI API.

Requires: pip install openai
Requires an OPENAI_API_KEY environment variable to be set.
"""

import json
import os
import re
import time

from openai import OpenAI

_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def call(model: str, prompt: str, max_tokens: int = 1024, retries: int = 3) -> str:
    """Call the model with a single user turn and return raw text output."""
    last_error = None
    for attempt in range(retries):
        try:
            response = _client.chat.completions.create(
                model=model,
                max_completion_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001 - broad on purpose, we retry
            last_error = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"LLM call failed after {retries} attempts: {last_error}")


def call_json(model: str, prompt: str, max_tokens: int = 1024, retries: int = 3) -> dict:
    """Call the model and parse the response as JSON.

    Strips markdown code fences if the model wraps its JSON in them, and
    retries the whole call (not just the parse) if parsing fails, since a
    fresh sample sometimes produces valid JSON when a previous one didn't.
    """
    last_error = None
    for attempt in range(retries):
        raw = call(model, prompt, max_tokens=max_tokens, retries=1)
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            last_error = e
            time.sleep(1)
    raise RuntimeError(f"Could not parse JSON after {retries} attempts: {last_error}\nLast raw output:\n{raw}")
