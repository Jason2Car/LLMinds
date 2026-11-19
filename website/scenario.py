"""The "stranded on the moon" scenario: pick and rank the 3 most important of 15 items."""

TOP_N = 3  # how many items the participant ranks

SCENARIO_TEXT = (
    f"From the 15 items below, choose the {TOP_N} that are most important to "
    f"survival and rank them from 1 (most important) to {TOP_N}."
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
]

ITEM_IDS = [i["id"] for i in ITEMS]
ITEM_NAMES = {i["id"]: i["name"] for i in ITEMS}


def is_valid_ranking(ranking) -> bool:
    """A ranking is TOP_N different item ids, most important first."""
    return (
        isinstance(ranking, list)
        and len(ranking) == TOP_N
        and len(set(ranking)) == TOP_N
        and all(item in ITEM_NAMES for item in ranking)
    )


def rank_change(before: list[str], after: list[str]) -> dict:
    """How far the final top-N moved from the initial one.

    An item outside the top N counts as position N + 1, so swapping in a new
    item moves both the item that came out and the one that went in.
    """
    outside = TOP_N + 1
    pos_before = {item: i + 1 for i, item in enumerate(before)}
    pos_after = {item: i + 1 for i, item in enumerate(after)}
    moves = {
        item: pos_after.get(item, outside) - pos_before.get(item, outside)
        for item in set(before) | set(after)
    }
    return {
        "total_displacement": sum(abs(d) for d in moves.values()),
        "items_moved": sum(1 for d in moves.values() if d != 0),
        "items_replaced": sum(1 for item in before if item not in after),
        "max_move": max(abs(d) for d in moves.values()),
        "per_item": moves,
    }
