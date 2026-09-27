"""Uniformly sampled authored symbolic triad backend."""

from __future__ import annotations

import secrets
from typing import Any


BACKEND_ID = "symbolic-prompt"
DISPLAY_NAME = "Random Symbolic Prompt"
BASE_WEIGHT = 10
USES_TIMESTAMP = False
REQUIRED_INPUTS: tuple[str, ...] = ()
BACKEND_SCHEMA = "spiral-oracle.backend.symbolic-prompt/v1"
REPLAY_SCHEMA = "spiral-oracle.replay.symbolic-prompt/v1"
CATALOG_VERSION = "symbolic-triad-en/v1"

SYMBOLS = (
    "Threshold",
    "Mirror",
    "Bridge",
    "Seed",
    "Vessel",
    "Labyrinth",
    "Lantern",
    "Tide",
    "Knot",
    "Echo",
    "Compass",
    "Window",
    "Mask",
    "Root",
    "Flame",
    "Empty Chair",
    "Broken Clock",
    "Door",
    "River",
    "Mountain",
    "Thread",
    "Garden",
    "Shadow",
    "Bell",
)

MOTIONS = (
    "approach",
    "withdraw",
    "wait",
    "reveal",
    "conceal",
    "divide",
    "join",
    "invert",
    "name",
    "release",
    "protect",
    "exchange",
    "return",
    "listen",
    "narrow",
    "widen",
)

LENSES = (
    "at the boundary",
    "from the smallest useful scale",
    "through another person's eyes",
    "before apparent completion",
    "after the apparent ending",
    "under time pressure",
    "without forcing",
    "with one constraint removed",
    "as a maintenance problem",
    "as a relationship",
    "as a reversible trial",
    "from the future looking back",
    "through what is absent",
    "through what repeats",
    "as a handoff",
    "in silence",
)


def validate_index(name: str, value: Any, size: int) -> int:
    if type(value) is not int or not 0 <= value < size:
        raise ValueError(f"{name} must be an integer from 0 through {size - 1}")
    return value


def render(symbol_index: int, motion_index: int, lens_index: int) -> dict[str, Any]:
    symbol_index = validate_index("symbol_index", symbol_index, len(SYMBOLS))
    motion_index = validate_index("motion_index", motion_index, len(MOTIONS))
    lens_index = validate_index("lens_index", lens_index, len(LENSES))

    symbol = SYMBOLS[symbol_index]
    motion = MOTIONS[motion_index]
    lens = LENSES[lens_index]
    return {
        "schema": BACKEND_SCHEMA,
        "method": {
            "name": "independent-uniform-symbolic-triad",
            "catalog_version": CATALOG_VERSION,
            "vocabulary_sizes": {
                "symbols": len(SYMBOLS),
                "motions": len(MOTIONS),
                "lenses": len(LENSES),
            },
            "authorship_disclosure": (
                "The vocabulary is authored and finite; random selection does not make it neutral."
            ),
        },
        "draw": {
            "symbol": {"index": symbol_index, "value": symbol},
            "motion": {"index": motion_index, "value": motion},
            "lens": {"index": lens_index, "value": lens},
        },
        "prompt": (
            f"Hold the image of the {symbol}. Ask what it would mean to {motion} {lens}."
        ),
    }


def generate(timestamp: str) -> tuple[dict[str, Any], dict[str, Any]]:
    _ = timestamp
    replay_payload = {
        "schema": REPLAY_SCHEMA,
        "catalog_version": CATALOG_VERSION,
        "symbol_index": secrets.randbelow(len(SYMBOLS)),
        "motion_index": secrets.randbelow(len(MOTIONS)),
        "lens_index": secrets.randbelow(len(LENSES)),
    }
    return replay(replay_payload, timestamp), replay_payload


def replay(payload: dict[str, Any], timestamp: str) -> dict[str, Any]:
    _ = timestamp
    expected = {
        "schema",
        "catalog_version",
        "symbol_index",
        "motion_index",
        "lens_index",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected
        or payload.get("schema") != REPLAY_SCHEMA
        or payload.get("catalog_version") != CATALOG_VERSION
    ):
        raise ValueError("invalid symbolic-prompt replay payload")
    return render(
        payload["symbol_index"],
        payload["motion_index"],
        payload["lens_index"],
    )
