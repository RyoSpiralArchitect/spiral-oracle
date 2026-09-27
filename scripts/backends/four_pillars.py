"""Replayable oracle-moment Four Pillars backend with explicit conventions."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from types import MappingProxyType
from typing import Any, Mapping

from . import _solar


BACKEND_ID = "spiral-four-pillars"
DISPLAY_NAME = "Spiral Four Pillars — Oracle Moment"
BASE_WEIGHT = 15
USES_TIMESTAMP = True
REQUIRED_INPUTS: tuple[str, ...] = ()
BACKEND_SCHEMA = "spiral-oracle.backend.four-pillars/v1"
REPLAY_SCHEMA = "spiral-oracle.replay.four-pillars/v1"
CATALOG_VERSION = "gan-zhi-identifiers-zh-latn/v1"
RULESET_VERSION = "li-chun-jie-civil-midnight/v1"
CATALOG_SHA256 = "ccaae2a8fd3dc19e60b72a7007340170c06ef2d79afde4ada9ba9f1dc2165cd3"


def _identifier(han: str, pinyin: str, **extra: str) -> Mapping[str, str]:
    return MappingProxyType({"han": han, "pinyin": pinyin, **extra})


STEMS = (
    _identifier("甲", "Jia"),
    _identifier("乙", "Yi"),
    _identifier("丙", "Bing"),
    _identifier("丁", "Ding"),
    _identifier("戊", "Wu"),
    _identifier("己", "Ji"),
    _identifier("庚", "Geng"),
    _identifier("辛", "Xin"),
    _identifier("壬", "Ren"),
    _identifier("癸", "Gui"),
)
BRANCHES = (
    _identifier("子", "Zi", animal="Rat"),
    _identifier("丑", "Chou", animal="Ox"),
    _identifier("寅", "Yin", animal="Tiger"),
    _identifier("卯", "Mao", animal="Rabbit"),
    _identifier("辰", "Chen", animal="Dragon"),
    _identifier("巳", "Si", animal="Snake"),
    _identifier("午", "Wu", animal="Horse"),
    _identifier("未", "Wei", animal="Goat"),
    _identifier("申", "Shen", animal="Monkey"),
    _identifier("酉", "You", animal="Rooster"),
    _identifier("戌", "Xu", animal="Dog"),
    _identifier("亥", "Hai", animal="Pig"),
)


def catalog_sha256() -> str:
    encoded = json.dumps(
        {
            "stems": [dict(stem) for stem in STEMS],
            "branches": [dict(branch) for branch in BRANCHES],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


if catalog_sha256() != CATALOG_SHA256:
    raise RuntimeError("Four Pillars catalog changed without a version update")


def civil_julian_day_number(civil_date: date) -> int:
    adjustment = (14 - civil_date.month) // 12
    year = civil_date.year + 4_800 - adjustment
    month = civil_date.month + 12 * adjustment - 3
    return (
        civil_date.day
        + (153 * month + 2) // 5
        + 365 * year
        + year // 4
        - year // 100
        + year // 400
        - 32_045
    )


def sexagenary_index(stem_index: int, branch_index: int) -> int:
    for index in range(60):
        if index % 10 == stem_index and index % 12 == branch_index:
            return index
    raise ValueError("stem and branch parity cannot form a sexagenary pair")


def pillar(stem_index: int, branch_index: int) -> dict[str, Any]:
    stem = STEMS[stem_index]
    branch = BRANCHES[branch_index]
    return {
        "sexagenary_index_zero_based": sexagenary_index(stem_index, branch_index),
        "stem_index": stem_index,
        "branch_index": branch_index,
        "stem": dict(stem),
        "branch": dict(branch),
        "han": stem["han"] + branch["han"],
        "latin": stem["pinyin"] + "-" + branch["pinyin"],
    }


def derive_indices(timestamp: str, solar_longitude_millidegrees: int) -> dict[str, Any]:
    moment = _solar.parse_moment(timestamp)
    if (
        type(solar_longitude_millidegrees) is not int
        or not 0 <= solar_longitude_millidegrees < _solar.MILLIDEGREES_PER_CIRCLE
    ):
        raise ValueError("solar longitude must be an integer from 0 through 359999")

    before_li_chun = moment.month <= 2 and solar_longitude_millidegrees < 315_000
    pillar_year = moment.year - int(before_li_chun)
    year_cycle = (pillar_year - 1_984) % 60
    year_stem = year_cycle % 10
    year_branch = year_cycle % 12

    solar_month_index = ((solar_longitude_millidegrees - 315_000) % 360_000) // 30_000
    month_branch = (2 + solar_month_index) % 12
    month_stem = ((year_stem % 5) * 2 + 2 + solar_month_index) % 10

    day_number = civil_julian_day_number(moment.date())
    day_cycle = (day_number + 49) % 60
    day_stem = day_cycle % 10
    day_branch = day_cycle % 12

    hour_branch = ((moment.hour + 1) // 2) % 12
    hour_stem = ((day_stem % 5) * 2 + hour_branch) % 10
    return {
        "pillar_year": pillar_year,
        "solar_month_index_zero_based_from_yin": solar_month_index,
        "civil_julian_day_number": day_number,
        "year": (year_stem, year_branch),
        "month": (month_stem, month_branch),
        "day": (day_stem, day_branch),
        "hour": (hour_stem, hour_branch),
    }


def replay_payload_for(timestamp: str) -> dict[str, Any]:
    moment = _solar.parse_moment(timestamp)
    solar_longitude = _solar.apparent_solar_longitude_millidegrees(timestamp)
    return {
        "schema": REPLAY_SCHEMA,
        "catalog_version": CATALOG_VERSION,
        "ruleset_version": RULESET_VERSION,
        "solar_algorithm_version": _solar.ALGORITHM_VERSION,
        "solar_longitude_millidegrees": solar_longitude,
        "local_civil_date": moment.date().isoformat(),
        "local_hour_zero_based": moment.hour,
        "utc_offset_seconds": _solar.utc_offset_seconds(moment),
    }


def render(timestamp: str, solar_longitude_millidegrees: int) -> dict[str, Any]:
    moment = _solar.parse_moment(timestamp)
    indices = derive_indices(timestamp, solar_longitude_millidegrees)
    pillars = {
        name: pillar(*indices[name]) for name in ("year", "month", "day", "hour")
    }
    return {
        "schema": BACKEND_SCHEMA,
        "method": {
            "name": "oracle-moment-four-pillars",
            "catalog_version": CATALOG_VERSION,
            "ruleset_version": RULESET_VERSION,
            "solar_algorithm_version": _solar.ALGORITHM_VERSION,
            "supported_years": {
                "minimum": _solar.MIN_SUPPORTED_YEAR,
                "maximum": _solar.MAX_SUPPORTED_YEAR,
            },
            "source_attested_basis": {
                "cycle": "ten stems and twelve branches paired into a 60-cycle",
                "structure": "year, month, day, and shichen form the Eight Characters",
                "solar_terms": "24 terms at 15-degree solar-longitude intervals",
            },
            "spiral_conventions": {
                "scope": "oracle moment, not a natal chart",
                "year_boundary": "Li Chun at 315 degrees solar longitude",
                "month_boundaries": (
                    "twelve 30-degree Jie sectors beginning with Yin at Li Chun"
                ),
                "day_boundary": "local civil midnight",
                "hour_branches": "Zi begins at 23:00 local civil time",
                "time_basis": (
                    "the timestamp's fixed UTC offset; no birthplace, longitude, "
                    "timezone-history lookup, or true-solar-time correction"
                ),
            },
            "randomness": (
                "none inside the backend; the selector chose the method randomly, "
                "then this method used the pre-captured timestamp"
            ),
            "catalog_sha256": CATALOG_SHA256,
            "interpretive_text_included": False,
        },
        "calendar_primitives": {
            "local_civil_date": moment.date().isoformat(),
            "local_hour_zero_based": moment.hour,
            "utc_offset_seconds": _solar.utc_offset_seconds(moment),
            "solar_longitude_millidegrees": solar_longitude_millidegrees,
            "solar_longitude_degrees": f"{solar_longitude_millidegrees / 1_000:.3f}",
            "pillar_year": indices["pillar_year"],
            "solar_month_index_zero_based_from_yin": indices[
                "solar_month_index_zero_based_from_yin"
            ],
            "civil_julian_day_number": indices["civil_julian_day_number"],
        },
        "pillars": pillars,
        "eight_characters": "".join(pillars[name]["han"] for name in pillars),
    }


def generate(timestamp: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = replay_payload_for(timestamp)
    return replay(payload, timestamp), payload


def replay(payload: dict[str, Any], timestamp: str) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "catalog_version",
        "ruleset_version",
        "solar_algorithm_version",
        "solar_longitude_millidegrees",
        "local_civil_date",
        "local_hour_zero_based",
        "utc_offset_seconds",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema") != REPLAY_SCHEMA
        or payload.get("catalog_version") != CATALOG_VERSION
        or payload.get("ruleset_version") != RULESET_VERSION
        or payload.get("solar_algorithm_version") != _solar.ALGORITHM_VERSION
    ):
        raise ValueError("invalid Four Pillars replay payload")
    expected = replay_payload_for(timestamp)
    if payload != expected:
        raise ValueError("Four Pillars replay payload does not match timestamp")
    return render(timestamp, payload["solar_longitude_millidegrees"])
