"""
Thin wrapper around the OpenAI API.

Requires: pip install openai
Reads the API key from config.env (in this same directory), which should
contain a single line:

    API_KEY=your_key_here
"""

import json
import os
import re
import time
import traceback

from openai import OpenAI

_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")


def _load_api_key(path: str = _ENV_FILE) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find {path}. Create a config.env file next to this "
            f"one containing a single line: API_KEY=your_key_here"
        )
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                if key.strip() == "API_KEY":
                    return value.strip().strip('"').strip("'")
    raise ValueError(f"No API_KEY entry found in {path}")


_client = OpenAI(api_key=_load_api_key())


def call(model: str, prompt: str, max_tokens: int = 1024, retries: int = 3) -> str:
    """Call the model with a single user turn and return raw text output."""
    last_error = None
    last_traceback = None
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
            last_traceback = traceback.format_exc()
            time.sleep(2 ** attempt)
    print("\n--- FULL TRACEBACK OF LAST ERROR ---")
    print(last_traceback)
    print("--- END TRACEBACK ---\n")
    raise RuntimeError(f"LLM call failed after {retries} attempts: {last_error}")


def call_json(model: str, prompt: str, max_tokens: int = 1024, retries: int = 3) -> dict:
    """Call the model and parse the response as JSON."""
    last_error = None
    raw = ""
    for attempt in range(retries):
        raw = call(model, prompt, max_tokens=max_tokens, retries=1)
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            last_error = e
            time.sleep(1)
    raise RuntimeError(f"Could not parse JSON after {retries} attempts: {last_error}\nLast raw output:\n{raw}")
