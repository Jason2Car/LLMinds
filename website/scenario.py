"""The "stranded on the moon" scenario: 20 items to rank by importance to survival."""

SCENARIO_TEXT = (
    "Your spaceship has crash-landed on the moon, 200 miles from the lunar "
    "base where your crew was due to rendezvous. Much of the equipment was "
    "destroyed. Survival depends on reaching the base, so you must choose the "
    "most critical items from what remains. Rank the 20 items below from "
    "1 (most important to survival) to 20 (least important)."
)

ITEMS = [
    {"id": "oxygen", "name": "Two 100 lb tanks of oxygen"},
    {"id": "water", "name": "20 gallons of water"},
    {"id": "star_map", "name": "Stellar map (of the moon's constellations)"},
    {"id": "food", "name": "Food concentrate"},
    {"id": "radio", "name": "Solar-powered FM receiver-transmitter"},
    {"id": "rope", "name": "50 feet of nylon rope"},
    {"id": "first_aid", "name": "First aid kit with injection needles"},
    {"id": "parachute", "name": "Parachute silk"},
    {"id": "raft", "name": "Self-inflating life raft"},
    {"id": "flares", "name": "Signal flares"},
    {"id": "pistols", "name": "Two .45 caliber pistols"},
    {"id": "milk", "name": "One case of dehydrated milk"},
    {"id": "heater", "name": "Portable heating unit"},
    {"id": "compass", "name": "Magnetic compass"},
    {"id": "matches", "name": "Box of matches"},
    {"id": "flashlight", "name": "Flashlight"},
    {"id": "telescope", "name": "Hand-held telescope"},
    {"id": "tape", "name": "Roll of duct tape"},
    {"id": "multitool", "name": "Multi-tool knife"},
    {"id": "blanket", "name": "Insulated emergency blanket"},
]

ITEM_IDS = [i["id"] for i in ITEMS]
ITEM_NAMES = {i["id"]: i["name"] for i in ITEMS}


def is_valid_ranking(ranking) -> bool:
    """A ranking is a list of all item ids, each exactly once, most important first."""
    return isinstance(ranking, list) and sorted(ranking) == sorted(ITEM_IDS)


def rank_change(before: list[str], after: list[str]) -> dict:
    """How far a final ranking moved from the initial one."""
    pos_before = {item: i + 1 for i, item in enumerate(before)}
    pos_after = {item: i + 1 for i, item in enumerate(after)}
    moves = {item: pos_after[item] - pos_before[item] for item in before}
    return {
        "total_displacement": sum(abs(d) for d in moves.values()),
        "items_moved": sum(1 for d in moves.values() if d != 0),
        "max_move": max(abs(d) for d in moves.values()),
        "per_item": moves,
    }
