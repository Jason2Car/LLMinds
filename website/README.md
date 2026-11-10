# Stranded on the Moon: persuasion study site

Participants rank 20 survival items, chat with an LLM crewmate (one of the
repo's archetype profiles) that tries to change their mind, re-rank, then rate
their confidence 1-7.

## Run

    pip install flask openai
    cd website && python app.py      # http://localhost:5001

Uses `../llm_client.py` and `../config.env` (API key), and the personas in
`../config/profiles/*/background.json`.

## Flow
1. `POST /api/start` assigns the **least-tested archetype** (ties random) and returns the 20 items.
2. `POST /api/ranking` saves the initial ranking; the persuader opens the chat.
3. `POST /api/message` for each user turn.
4. `POST /api/final` saves the re-ranking.
5. `POST /api/confidence` (1-7) writes the record.

## Data
`data/results.jsonl`, one JSON line per completed test: archetype,
`messages_before_change` (user messages sent before submitting the final
ranking), initial/final rankings, `total_displacement` (sum of absolute rank
moves), `items_moved`, `max_move`, `confidence`, transcript. `GET /api/tally`
gives completed tests per archetype (derived from that file).

## Notes
- In-progress sessions live in memory; only completed tests are saved or tallied.
- The persuader argues for *changes*, not for a "correct" answer.
