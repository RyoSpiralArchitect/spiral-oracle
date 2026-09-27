"""Replayable three-coin I Ching backend for Spiral Oracle.

Mechanics and lookup references:

- https://hexadecimal.uoregon.edu/ching/explain.html
- https://ccnmtl.columbia.edu/services/dropoff/china_civ_temp/week02/pdfs/iching.pdf
- https://plato.stanford.edu/entries/chinese-change/
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any, Sequence


BACKEND_ID = "spiral-iching"
DISPLAY_NAME = "Spiral I Ching"
BASE_WEIGHT = 30
USES_TIMESTAMP = False
REQUIRED_INPUTS: tuple[str, ...] = ()
BACKEND_SCHEMA = "spiral-oracle.backend.iching/v1"
REPLAY_SCHEMA = "spiral-oracle.replay.iching/v1"
RULESET_VERSION = "three-coin-king-wen/v1"

COIN_VALUE = {"H": 3, "T": 2}
MOVING_VALUES = {6, 9}

# Bit strings are ordered from the bottom line to the top line.
TRIGRAMS: dict[str, dict[str, str]] = {
    "111": {"han": "乾", "pinyin": "Qián", "image": "Heaven", "symbol": "☰"},
    "110": {"han": "兌", "pinyin": "Duì", "image": "Lake", "symbol": "☱"},
    "101": {"han": "離", "pinyin": "Lí", "image": "Fire", "symbol": "☲"},
    "100": {"han": "震", "pinyin": "Zhèn", "image": "Thunder", "symbol": "☳"},
    "011": {"han": "巽", "pinyin": "Xùn", "image": "Wind", "symbol": "☴"},
    "010": {"han": "坎", "pinyin": "Kǎn", "image": "Water", "symbol": "☵"},
    "001": {"han": "艮", "pinyin": "Gèn", "image": "Mountain", "symbol": "☶"},
    "000": {"han": "坤", "pinyin": "Kūn", "image": "Earth", "symbol": "☷"},
}

# Rows are lower trigrams; columns are upper trigrams.
TRIGRAM_ORDER = ("111", "110", "101", "100", "011", "010", "001", "000")
KING_WEN_MATRIX = (
    (1, 43, 14, 34, 9, 5, 26, 11),
    (10, 58, 38, 54, 61, 60, 41, 19),
    (13, 49, 30, 55, 37, 63, 22, 36),
    (25, 17, 21, 51, 42, 3, 27, 24),
    (44, 28, 50, 32, 57, 48, 18, 46),
    (6, 47, 64, 40, 59, 29, 4, 7),
    (33, 31, 56, 62, 53, 39, 52, 15),
    (12, 45, 35, 16, 20, 8, 23, 2),
)

# Conventional short identifiers only; no judgment or commentary text is bundled.
HEXAGRAMS: dict[int, tuple[str, str, str]] = {
    1: ("乾", "Qián", "The Creative"),
    2: ("坤", "Kūn", "The Receptive"),
    3: ("屯", "Zhūn", "Difficulty at the Beginning"),
    4: ("蒙", "Méng", "Youthful Folly"),
    5: ("需", "Xū", "Waiting"),
    6: ("訟", "Sòng", "Conflict"),
    7: ("師", "Shī", "The Army"),
    8: ("比", "Bǐ", "Holding Together"),
    9: ("小畜", "Xiǎo Xù", "Small Taming"),
    10: ("履", "Lǚ", "Treading"),
    11: ("泰", "Tài", "Peace"),
    12: ("否", "Pǐ", "Standstill"),
    13: ("同人", "Tóng Rén", "Fellowship"),
    14: ("大有", "Dà Yǒu", "Great Possession"),
    15: ("謙", "Qiān", "Modesty"),
    16: ("豫", "Yù", "Enthusiasm"),
    17: ("隨", "Suí", "Following"),
    18: ("蠱", "Gǔ", "Work on the Decayed"),
    19: ("臨", "Lín", "Approach"),
    20: ("觀", "Guān", "Contemplation"),
    21: ("噬嗑", "Shì Kè", "Biting Through"),
    22: ("賁", "Bì", "Grace"),
    23: ("剝", "Bō", "Splitting Apart"),
    24: ("復", "Fù", "Return"),
    25: ("无妄", "Wú Wàng", "Innocence"),
    26: ("大畜", "Dà Chù", "Great Accumulation"),
    27: ("頤", "Yí", "Nourishment"),
    28: ("大過", "Dà Guò", "Great Exceeding"),
    29: ("坎", "Kǎn", "The Abyss"),
    30: ("離", "Lí", "Clinging Fire"),
    31: ("咸", "Xián", "Influence"),
    32: ("恆", "Héng", "Duration"),
    33: ("遯", "Dùn", "Retreat"),
    34: ("大壯", "Dà Zhuàng", "Great Power"),
    35: ("晉", "Jìn", "Progress"),
    36: ("明夷", "Míng Yí", "Darkening of the Light"),
    37: ("家人", "Jiā Rén", "The Family"),
    38: ("睽", "Kuí", "Opposition"),
    39: ("蹇", "Jiǎn", "Obstruction"),
    40: ("解", "Xiè", "Deliverance"),
    41: ("損", "Sǔn", "Decrease"),
    42: ("益", "Yì", "Increase"),
    43: ("夬", "Guài", "Breakthrough"),
    44: ("姤", "Gòu", "Coming to Meet"),
    45: ("萃", "Cuì", "Gathering Together"),
    46: ("升", "Shēng", "Pushing Upward"),
    47: ("困", "Kùn", "Oppression"),
    48: ("井", "Jǐng", "The Well"),
    49: ("革", "Gé", "Revolution"),
    50: ("鼎", "Dǐng", "The Caldron"),
    51: ("震", "Zhèn", "The Arousing"),
    52: ("艮", "Gèn", "Keeping Still"),
    53: ("漸", "Jiàn", "Development"),
    54: ("歸妹", "Guī Mèi", "The Marrying Maiden"),
    55: ("豐", "Fēng", "Abundance"),
    56: ("旅", "Lǚ", "The Wanderer"),
    57: ("巽", "Xùn", "The Gentle"),
    58: ("兌", "Duì", "The Joyous"),
    59: ("渙", "Huàn", "Dispersion"),
    60: ("節", "Jié", "Limitation"),
    61: ("中孚", "Zhōng Fú", "Inner Truth"),
    62: ("小過", "Xiǎo Guò", "Preponderance of the Small"),
    63: ("既濟", "Jì Jì", "After Completion"),
    64: ("未濟", "Wèi Jì", "Before Completion"),
}


def validate_coin_groups(groups: Sequence[str]) -> list[str]:
    if not isinstance(groups, (list, tuple)) or len(groups) != 6:
        raise ValueError("I Ching replay requires exactly six coin groups")
    normalized = []
    for group in groups:
        if not isinstance(group, str):
            raise ValueError("each coin group must be a string")
        value = group.upper()
        if len(value) != 3 or any(coin not in COIN_VALUE for coin in value):
            raise ValueError(
                "each coin group must contain exactly three H/T characters"
            )
        normalized.append(value)
    return normalized


def random_coin_groups() -> list[str]:
    return ["".join(secrets.choice(("H", "T")) for _ in range(3)) for _ in range(6)]


def line_value(group: str) -> int:
    return sum(COIN_VALUE[coin] for coin in group)


def primary_bit(value: int) -> int:
    return 1 if value % 2 else 0


def relating_bit(value: int) -> int:
    bit = primary_bit(value)
    return 1 - bit if value in MOVING_VALUES else bit


def trigram_for(bits: Sequence[int]) -> dict[str, str]:
    key = "".join(str(bit) for bit in bits)
    return {"bits_bottom_to_top": key, **TRIGRAMS[key]}


def hexagram_number(bits: Sequence[int]) -> int:
    if len(bits) != 6 or any(bit not in (0, 1) for bit in bits):
        raise ValueError("a hexagram requires exactly six yin/yang bits")
    lower = "".join(str(bit) for bit in bits[:3])
    upper = "".join(str(bit) for bit in bits[3:])
    return KING_WEN_MATRIX[TRIGRAM_ORDER.index(lower)][TRIGRAM_ORDER.index(upper)]


def describe_hexagram(bits: Sequence[int]) -> dict[str, Any]:
    number = hexagram_number(bits)
    han, pinyin, english_name = HEXAGRAMS[number]
    return {
        "number": number,
        "unicode": chr(0x4DC0 + number - 1),
        "han": han,
        "pinyin": pinyin,
        "english_name": english_name,
        "line_bits_bottom_to_top": list(bits),
        "lower_trigram": trigram_for(bits[:3]),
        "upper_trigram": trigram_for(bits[3:]),
    }


def cast(groups: Sequence[str]) -> dict[str, Any]:
    normalized = validate_coin_groups(groups)
    values = [line_value(group) for group in normalized]
    primary_bits = [primary_bit(value) for value in values]
    relating_bits = [relating_bit(value) for value in values]
    moving_lines = [
        position
        for position, value in enumerate(values, start=1)
        if value in MOVING_VALUES
    ]
    raw_cast = ",".join(normalized)

    lines = []
    for position, (group, value, before, after) in enumerate(
        zip(normalized, values, primary_bits, relating_bits), start=1
    ):
        lines.append(
            {
                "position": position,
                "coins": group,
                "value": value,
                "primary": "yang" if before else "yin",
                "moving": value in MOVING_VALUES,
                "relating": "yang" if after else "yin",
            }
        )

    return {
        "schema": BACKEND_SCHEMA,
        "method": {
            "name": "three-coin",
            "ruleset_version": RULESET_VERSION,
            "coin_values": {"heads": 3, "tails": 2},
            "line_value_probabilities": {
                "6": "1/8",
                "7": "3/8",
                "8": "3/8",
                "9": "1/8",
            },
            "line_order": "bottom-to-top",
        },
        "raw_cast_bottom_to_top": raw_cast,
        "raw_cast_sha256": hashlib.sha256(raw_cast.encode("ascii")).hexdigest(),
        "lines_bottom_to_top": lines,
        "moving_lines": moving_lines,
        "primary_hexagram": describe_hexagram(primary_bits),
        "relating_hexagram": describe_hexagram(relating_bits) if moving_lines else None,
    }


def generate(timestamp: str) -> tuple[dict[str, Any], dict[str, Any]]:
    _ = timestamp
    groups = random_coin_groups()
    return cast(groups), {
        "schema": REPLAY_SCHEMA,
        "ruleset_version": RULESET_VERSION,
        "coins_bottom_to_top": groups,
    }


def replay(payload: dict[str, Any], timestamp: str) -> dict[str, Any]:
    _ = timestamp
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema", "ruleset_version", "coins_bottom_to_top"}
        or payload.get("schema") != REPLAY_SCHEMA
        or payload.get("ruleset_version") != RULESET_VERSION
    ):
        raise ValueError("invalid I Ching replay payload")
    return cast(payload["coins_bottom_to_top"])
