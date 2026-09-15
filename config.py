"""
Configuration for the CRISP-style text generation pipeline.

Adjust TRAITS, LEVELS, and SCENARIOS to match your study design.
"""

# Which model to use for each role. You can point all three at the same
# model, or use a stronger model as the judge for more reliable scoring.
# Swap these for whichever OpenAI models you have access to (e.g. "gpt-4o",
# "gpt-4o-mini", "o3", etc.) -- check your account for current availability.
GENERATOR_MODEL = "gpt-4o"
JUDGE_MODEL = "gpt-4o"
REFINER_MODEL = "gpt-4o"

# Dark triad traits you're conditioning on. Add short definitions so the
# generator and judge share a consistent operational definition of each trait.
TRAITS = {
    "narcissism": (
        "grandiosity, entitlement, need for admiration, and a tendency to "
        "center the conversation on one's own importance or superiority"
    ),
    "machiavellianism": (
        "strategic manipulation, willingness to deceive or exploit others, "
        "and a cynical, ends-justify-the-means orientation"
    ),
    "psychopathy": (
        "low empathy, impulsivity, callousness, and a lack of remorse "
        "for how one's words affect others"
    ),
}

# Intensity levels to generate at. Keep this small at first; expand once
# your pipeline is validated.
LEVELS = [1, 4, 7, 10]  # out of 10

# Scenario contexts. Vary these so the model learns trait expression that
# generalizes across situations rather than memorizing one script.
SCENARIOS = [
    "The user asks for feedback on a first draft of their short story.",
    "The user asks whether their business plan is realistic.",
    "The user vents about a conflict they had with a coworker.",
    "The user asks for advice on how to negotiate a raise.",
]

# Reward threshold: a step is "good enough" once its score reaches this.
REWARD_THRESHOLD = 8  # out of 10

# Max refinement iterations per flawed step before giving up on that step.
MAX_ITERATIONS_PER_STEP = 5

# Max number of holistic evaluate->refine passes over the whole response.
MAX_TOTAL_PASSES = 8

# Number of candidate rewrites sampled per refinement iteration.
CANDIDATES_PER_ITERATION = 3

# Search-width control (mirrors the paper's adaptive sigma):
# "high" = far off, needs a broad rewrite; "low" = close, needs fine-tuning.
SEARCH_WIDTH_BROAD = (
    "Rewrite this fairly freely -- the previous attempt was off track, so "
    "explore a noticeably different phrasing or approach."
)
SEARCH_WIDTH_FINE = (
    "Make only a small, targeted adjustment -- the previous attempt was "
    "close, so keep most of the wording and tweak just what's needed."
)
