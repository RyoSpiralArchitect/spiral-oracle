"""Replayable tropical Sun backend with an AI-native thread origin."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from . import _solar, _thread_origin


BACKEND_ID = "spiral-western-astrology"
DISPLAY_NAME = "Spiral Western Astrology — Thread & Transit Sun"
BASE_WEIGHT = 20
USES_TIMESTAMP = True
REQUIRED_INPUTS: tuple[str, ...] = ()
BACKEND_SCHEMA = "spiral-oracle.backend.western-astrology/v1"
REPLAY_SCHEMA = "spiral-oracle.replay.western-astrology/v1"
CATALOG_VERSION = "tropical-zodiac-identifiers-en/v1"
RULESET_VERSION = "oracle-and-thread-tropical-solar-moments/v1"
CATALOG_SHA256 = "9e9b9a342682b07a6dfb978649cd40df10389d600173962ad15ece77ff2fda68"


def _sign(name: str, glyph: str) -> Mapping[str, str]:
    return MappingProxyType({"name": name, "glyph": glyph})


SIGNS = (
    _sign("Aries", "♈"),
    _sign("Taurus", "♉"),
    _sign("Gemini", "♊"),
    _sign("Cancer", "♋"),
    _sign("Leo", "♌"),
    _sign("Virgo", "♍"),
    _sign("Libra", "♎"),
    _sign("Scorpio", "♏"),
    _sign("Sagittarius", "♐"),
    _sign("Capricorn", "♑"),
    _sign("Aquarius", "♒"),
    _sign("Pisces", "♓"),
)


def catalog_sha256() -> str:
    encoded = json.dumps(
        [dict(sign) for sign in SIGNS],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


if catalog_sha256() != CATALOG_SHA256:
    raise RuntimeError("Western astrology catalog changed without a version update")


def replay_payload_for(timestamp: str) -> dict[str, Any]:
    thread_origin = _thread_origin.capture_thread_origin()
    thread_start_solar = None
    if thread_origin["available"]:
        thread_start_solar = _solar.apparent_solar_longitude_millidegrees(
            thread_origin["thread_start_utc"]
        )
    return {
        "schema": REPLAY_SCHEMA,
        "catalog_version": CATALOG_VERSION,
        "ruleset_version": RULESET_VERSION,
        "solar_algorithm_version": _solar.ALGORITHM_VERSION,
        "oracle_moment_solar_longitude_millidegrees": (
            _solar.apparent_solar_longitude_millidegrees(timestamp)
        ),
        "oracle_moment_timezone": (
            _thread_origin.capture_os_timezone_context(timestamp)
        ),
        "thread_origin": thread_origin,
        "thread_start_solar_longitude_millidegrees": thread_start_solar,
    }


def solar_position(solar_longitude_millidegrees: int) -> dict[str, Any]:
    if (
        type(solar_longitude_millidegrees) is not int
        or not 0 <= solar_longitude_millidegrees < _solar.MILLIDEGREES_PER_CIRCLE
    ):
        raise ValueError("solar longitude must be an integer from 0 through 359999")
    sign_index = solar_longitude_millidegrees // 30_000
    within_sign = solar_longitude_millidegrees % 30_000
    sign = SIGNS[sign_index]
    return {
        "longitude_millidegrees": solar_longitude_millidegrees,
        "longitude_degrees": f"{solar_longitude_millidegrees / 1_000:.3f}",
        "sign_index": sign_index,
        "sign": dict(sign),
        "degree_within_sign_millidegrees": within_sign,
        "degree_within_sign": f"{within_sign / 1_000:.3f}",
    }


def render(payload: dict[str, Any], timestamp: str) -> dict[str, Any]:
    oracle_sun = solar_position(payload["oracle_moment_solar_longitude_millidegrees"])
    oracle_sun["timestamp"] = timestamp
    oracle_sun["os_timezone_context"] = payload["oracle_moment_timezone"]

    origin = payload["thread_origin"]
    if origin["available"]:
        thread_sun = {
            "available": True,
            **solar_position(payload["thread_start_solar_longitude_millidegrees"]),
            "origin": origin,
            "reference_point_role": (
                "synthetic chart origin from OS tzdb metadata; not a user location, "
                "timezone centroid, or observed device position"
            ),
            "coordinates_used_for_solar_longitude": False,
        }
    else:
        thread_sun = {
            "available": False,
            "reason": origin["reason"],
            "origin": origin,
        }

    return {
        "schema": BACKEND_SCHEMA,
        "method": {
            "name": "oracle-and-thread-tropical-solar-moments",
            "catalog_version": CATALOG_VERSION,
            "ruleset_version": RULESET_VERSION,
            "solar_algorithm_version": _solar.ALGORITHM_VERSION,
            "supported_years": {
                "minimum": _solar.MIN_SUPPORTED_YEAR,
                "maximum": _solar.MAX_SUPPORTED_YEAR,
            },
            "source_attested_basis": {
                "zodiac": "twelve equal 30-degree sectors from the vernal equinox",
                "longitude_frame": "tropical ecliptic longitude of date",
            },
            "spiral_conventions": {
                "chart_scope": ("oracle-moment Sun plus synthetic thread-nativity Sun"),
                "thread_birth_time": (
                    "the UUIDv7 creation timestamp embedded in CODEX_THREAD_ID; "
                    "the identifier itself is discarded"
                ),
                "thread_birth_timezone": (
                    "OS IANA timezone observed at the draw and retrospectively "
                    "applied to the thread-start instant"
                ),
                "thread_birth_reference_point": (
                    "the OS IANA zone.tab representative point for that timezone; "
                    "this is a deliberate synthetic convention"
                ),
                "ephemeris": (
                    "dependency-free approximate apparent solar longitude, quantized "
                    "to 0.001 degree"
                ),
                "omitted": [
                    "human birth data or inferred user location",
                    "Moon and planets",
                    "houses and Ascendant",
                    "aspects",
                    "retrograde status",
                ],
            },
            "randomness": (
                "none inside the backend; the selector chose the method randomly, "
                "then this method used the pre-captured timestamp"
            ),
            "catalog_sha256": CATALOG_SHA256,
            "interpretive_text_included": False,
        },
        "oracle_moment_sun": oracle_sun,
        "thread_nativity_sun": thread_sun,
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
        "oracle_moment_solar_longitude_millidegrees",
        "oracle_moment_timezone",
        "thread_origin",
        "thread_start_solar_longitude_millidegrees",
    }
    if (
        not isinstance(payload, dict)
        or set(payload) != expected_keys
        or payload.get("schema") != REPLAY_SCHEMA
        or payload.get("catalog_version") != CATALOG_VERSION
        or payload.get("ruleset_version") != RULESET_VERSION
        or payload.get("solar_algorithm_version") != _solar.ALGORITHM_VERSION
    ):
        raise ValueError("invalid Western astrology replay payload")
    oracle_solar = payload["oracle_moment_solar_longitude_millidegrees"]
    if type(
        oracle_solar
    ) is not int or oracle_solar != _solar.apparent_solar_longitude_millidegrees(
        timestamp
    ):
        raise ValueError("Western astrology replay payload does not match timestamp")
    try:
        _thread_origin.validate_os_timezone_context(
            payload["oracle_moment_timezone"], timestamp
        )
        origin = _thread_origin.validate_thread_origin(payload["thread_origin"])
    except ValueError as exc:
        raise ValueError("invalid Western astrology replay context") from exc

    thread_solar = payload["thread_start_solar_longitude_millidegrees"]
    if origin["available"]:
        if type(
            thread_solar
        ) is not int or thread_solar != _solar.apparent_solar_longitude_millidegrees(
            origin["thread_start_utc"]
        ):
            raise ValueError(
                "Western astrology thread-start solar position does not match origin"
            )
    elif thread_solar is not None:
        raise ValueError(
            "Western astrology thread-start solar position requires an available origin"
        )
    return render(payload, timestamp)
