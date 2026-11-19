"""
Loads config files for a given personality profile.

Everything task-specific lives under config/tasks/<task>/ (e.g. "assembly",
"moon"): a questions.json for the tuner and one folder per archetype under
profiles/<name>/. Each task has its own baseline and personality models,
since a task can bring out different personalities. Each profile folder holds:
    weights.json      -- target trait vector, tolerance, iteration limits
    background.json   -- character role, backstory and tone notes

Also loads the active task's fixed question set (questions.json) used by
optimize mode and baseline calibration.

Also holds which model plays each role in the CRISP loop, and reads the
voice-input settings (VOICE_INPUT, WHISPER_MODEL, VOICE_INPUT_DURATION)
from config.env.
"""

import json
import os

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
_TASKS_DIR = os.path.join(_CONFIG_DIR, "tasks")
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.env")

AVAILABLE_PROFILES = ["narcissistic", "machiavellian", "psychopathic", "baseline"]
AVAILABLE_TASKS = sorted(
    d for d in os.listdir(_TASKS_DIR) if os.path.isdir(os.path.join(_TASKS_DIR, d))
)
DEFAULT_TASK = "assembly"

_active_profile = None
_active_task = DEFAULT_TASK


def _load_env(path: str = _ENV_FILE) -> dict:
    values = {}
    if not os.path.exists(path):
        return values
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_env = _load_env()

# Voice input: when VOICE_INPUT=true in config.env, app.py records from the
# microphone and transcribes with OpenAI Whisper instead of reading typed
# text. See voice/voice_input.py.
VOICE_INPUT_ENABLED = _env.get("VOICE_INPUT", "false").strip().lower() in ("1", "true", "yes")
WHISPER_MODEL = _env.get("WHISPER_MODEL", "whisper-1")
VOICE_INPUT_DURATION = int(_env.get("VOICE_INPUT_DURATION", "5"))

# Voice output: when VOICE_OUTPUT=true in config.env, app.py reads each
# assistant reply aloud with OpenAI text-to-speech (in addition to printing
# it). See voice/voice_output.py. Keep the voice and instructions identical across
# all four profiles so the voice itself is not a confound: the personality
# should come from the words, not the delivery.
VOICE_OUTPUT_ENABLED = _env.get("VOICE_OUTPUT", "false").strip().lower() in ("1", "true", "yes")
TTS_MODEL = _env.get("TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = _env.get("TTS_VOICE", "alloy")
TTS_INSTRUCTIONS = _env.get(
    "TTS_INSTRUCTIONS",
    "Speak clearly at a steady, natural pace in a neutral tone.",
)

TRAIT_DIMENSIONS = [
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
    "narcissism",
    "machiavellianism",
    "psychopathy",
]

GENERATOR_MODEL = "gpt-4o"
EVALUATOR_MODEL = "gpt-4o"
REFINER_MODEL = "gpt-4o"
INTERVIEWER_MODEL = "gpt-4o"
GRADER_MODEL = "gpt-4o"

# Interview mode: the interviewer always asks MIN_TURNS questions, may end
# early (after that) once it has seen enough, and is cut off at MAX_TURNS.
INTERVIEW_MIN_TURNS = 5
INTERVIEW_MAX_TURNS = 10


def profile_dir(task: str, profile: str) -> str:
    """Folder holding a profile's weights.json and background.json for a task."""
    return os.path.join(_TASKS_DIR, task, "profiles", profile)


def set_task(name: str) -> None:
    """Select the task whose profiles and questions are loaded. Call before set_profile."""
    global _active_task
    if name not in AVAILABLE_TASKS:
        raise ValueError(f"Unknown task '{name}'. Available: {AVAILABLE_TASKS}")
    _active_task = name


def get_active_task() -> str:
    return _active_task


def set_profile(name: str) -> None:
    global _active_profile
    if name not in AVAILABLE_PROFILES:
        raise ValueError(
            f"Unknown profile '{name}'. Available: {AVAILABLE_PROFILES}"
        )
    folder = profile_dir(_active_task, name)
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Profile directory not found: {folder}")
    _active_profile = name


def get_active_profile() -> str | None:
    return _active_profile


# The baseline profile is the bare OpenAI model: its target scores were
# measured from direct calls (scripts/calibrate_baseline.py), so it is used the same
# way, with no backstory, tone notes or CRISP loop.
BARE_PROFILE = "baseline"


def uses_bare_model() -> bool:
    return _active_profile == BARE_PROFILE


def _resolve_paths() -> tuple[str, str]:
    if not _active_profile:
        raise RuntimeError("No profile selected: call config.set_profile() first.")
    folder = profile_dir(_active_task, _active_profile)
    return (
        os.path.join(folder, "weights.json"),
        os.path.join(folder, "background.json"),
    )


def load_weights(path: str | None = None) -> dict:
    if path is None:
        path = _resolve_paths()[0]
    with open(path) as f:
        weights = json.load(f)

    missing = set(TRAIT_DIMENSIONS) - set(weights["target_profile"])
    if missing:
        raise ValueError(f"weights.json target_profile is missing traits: {missing}")

    return weights


def load_background(path: str | None = None) -> dict:
    if path is None:
        path = _resolve_paths()[1]
    with open(path) as f:
        return json.load(f)


def load_questions(path: str | None = None) -> list[str]:
    """The active task's fixed user questions for optimize mode and calibration, asked in order.

    Using the same questions every round keeps rounds comparable for the tuner.
    """
    if path is None:
        path = os.path.join(_TASKS_DIR, _active_task, "questions.json")
    with open(path) as f:
        questions = json.load(f)["questions"]
    if not questions:
        raise ValueError(f"{path} has no questions")
    return questions


def save_tone_notes(tone_notes: str, path: str | None = None) -> None:
    """Overwrite tone_notes in the active profile's background.json."""
    _save_background_field("tone_notes", tone_notes, path)


def save_backstory(backstory: str, path: str | None = None) -> None:
    """Overwrite backstory in the active profile's background.json."""
    _save_background_field("backstory", backstory, path)


def _save_background_field(field: str, value: str, path: str | None) -> None:
    if path is None:
        path = _resolve_paths()[1]
    with open(path) as f:
        background = json.load(f)
    background[field] = value
    with open(path, "w") as f:
        json.dump(background, f, indent=2)
        f.write("\n")
