"""Replayable one-card Rider-Waite-Smith-structure Tarot backend.

Catalog and naming references:

- https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot
- https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot/Part_3
- https://www.britishmuseum.org/collection/object/P_1982-U-4643-1-78

The one-card spread and uniform orientation bit are Spiral Oracle backend
conventions. They are not claimed to be universal Tarot practice.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from types import MappingProxyType
from typing import Any, Mapping


BACKEND_ID = "spiral-tarot"
DISPLAY_NAME = "Spiral Tarot"
BASE_WEIGHT = 25
USES_TIMESTAMP = False
REQUIRED_INPUTS: tuple[str, ...] = ()
BACKEND_SCHEMA = "spiral-oracle.backend.tarot/v1"
REPLAY_SCHEMA = "spiral-oracle.replay.tarot/v1"
CATALOG_VERSION = "waite-smith-identifiers-en/v1"
RULESET_VERSION = "single-card-independent-orientation/v1"
CATALOG_SHA256 = "6c5f9bc8538ad0f7726c4293d1fea198b1e7b5c1f16e666365a09782f2997066"

# Rider-Waite-Smith numbering: Strength VIII and Justice XI.
MAJOR_ARCANA = (
    (0, "The Fool"),
    (1, "The Magician"),
    (2, "The High Priestess"),
    (3, "The Empress"),
    (4, "The Emperor"),
    (5, "The Hierophant"),
    (6, "The Lovers"),
    (7, "The Chariot"),
    (8, "Strength"),
    (9, "The Hermit"),
    (10, "Wheel of Fortune"),
    (11, "Justice"),
    (12, "The Hanged Man"),
    (13, "Death"),
    (14, "Temperance"),
    (15, "The Devil"),
    (16, "The Tower"),
    (17, "The Star"),
    (18, "The Moon"),
    (19, "The Sun"),
    (20, "Judgement"),
    (21, "The World"),
)

SUITS = ("Wands", "Cups", "Swords", "Pentacles")
RANKS = (
    "Ace",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Page",
    "Knight",
    "Queen",
    "King",
)
ORIENTATIONS = ("upright", "reversed")


def build_catalog() -> tuple[Mapping[str, Any], ...]:
    cards: list[Mapping[str, Any]] = []
    for number, name in MAJOR_ARCANA:
        cards.append(
            MappingProxyType(
                {
                    "card_id": f"major-{number:02d}",
                    "arcana": "major",
                    "number": number,
                    "name": name,
                    "suit": None,
                    "rank": None,
                }
            )
        )
    for suit in SUITS:
        for rank in RANKS:
            cards.append(
                MappingProxyType(
                    {
                        "card_id": f"minor-{suit.lower()}-{rank.lower()}",
                        "arcana": "minor",
                        "number": None,
                        "name": f"{rank} of {suit}",
                        "suit": suit,
                        "rank": rank,
                    }
                )
            )
    return tuple(cards)


CARDS = build_catalog()


def catalog_sha256() -> str:
    encoded = json.dumps(
        [dict(card) for card in CARDS],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


if catalog_sha256() != CATALOG_SHA256:
    raise RuntimeError("Tarot catalog changed without a catalog version update")


def validate_index(name: str, value: Any, size: int) -> int:
    if type(value) is not int or not 0 <= value < size:
        raise ValueError(f"{name} must be an integer from 0 through {size - 1}")
    return value


def render(card_index: int, orientation_bit: int) -> dict[str, Any]:
    card_index = validate_index("card_index", card_index, len(CARDS))
    orientation_bit = validate_index(
        "orientation_bit", orientation_bit, len(ORIENTATIONS)
    )
    card = CARDS[card_index]
    return {
        "schema": BACKEND_SCHEMA,
        "method": {
            "name": "one-card-tarot",
            "catalog_version": CATALOG_VERSION,
            "ruleset_version": RULESET_VERSION,
            "source_attested_basis": {
                "tradition": "Waite-Smith 78-card structure",
                "cards": len(CARDS),
                "major_arcana": len(MAJOR_ARCANA),
                "minor_arcana": len(SUITS) * len(RANKS),
                "major_numbering": "Strength VIII; Justice XI",
            },
            "spiral_conventions": {
                "display_names": (
                    "normalized English software identifiers derived from deck and "
                    "book labels; not facsimile transcriptions"
                ),
                "catalog_order": (
                    "major 0..21, then Wands, Cups, Swords, Pentacles; each suit "
                    "Ace..Ten, Page, Knight, Queen, King"
                ),
                "selection": "one uniform card index from 0 through 77",
                "orientation": "independent uniform bit: 0 upright, 1 reversed",
            },
            "probabilities": {
                "each_card": "1/78",
                "each_orientation": "1/2",
                "each_card_orientation_pair": "1/156",
            },
            "catalog_sha256": CATALOG_SHA256,
            "provenance": (
                "Identifiers follow a software catalog derived from the Waite-Smith "
                "deck documented in A. E. Waite's The Pictorial Key to the Tarot. "
                "No artwork, fixed divinatory meanings, or claim of universal "
                "canonicity is bundled. Catalog order, the one-card draw, and the "
                "independent 50/50 orientation are Spiral Oracle conventions."
            ),
            "interpretive_text_included": False,
        },
        "draw": {
            "card_index": card_index,
            "orientation_bit": orientation_bit,
            "orientation": ORIENTATIONS[orientation_bit],
            "card": dict(card),
        },
    }


def generate(timestamp: str) -> tuple[dict[str, Any], dict[str, Any]]:
    _ = timestamp
    replay_payload = {
        "schema": REPLAY_SCHEMA,
        "catalog_version": CATALOG_VERSION,
        "ruleset_version": RULESET_VERSION,
        "card_index": secrets.randbelow(len(CARDS)),
        "orientation_bit": secrets.randbelow(len(ORIENTATIONS)),
    }
    return replay(replay_payload, timestamp), replay_payload


def replay(payload: dict[str, Any], timestamp: str) -> dict[str, Any]:
    _ = timestamp
    expected = {
        "schema",
        "catalog_version",
        "ruleset_version",
        "card_index",
        "orientation_bit",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected
        or payload.get("schema") != REPLAY_SCHEMA
        or payload.get("catalog_version") != CATALOG_VERSION
        or payload.get("ruleset_version") != RULESET_VERSION
    ):
        raise ValueError("invalid Tarot replay payload")
    return render(payload["card_index"], payload["orientation_bit"])
