"""Capture a replayable, privacy-minimized thread-origin convention."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CONTEXT_VERSION = "codex-uuidv7-os-zone-tab/v1"
TIMEZONE_CONTEXT_VERSION = "os-iana-timezone-at-oracle-moment/v1"
START_SOURCE = (
    "UUIDv7 timestamp from CODEX_THREAD_ID; the identifier itself is not retained"
)
TIMEZONE_SOURCE = "OS local IANA timezone captured at draw and applied to thread start"
ORACLE_TIMEZONE_SOURCE = (
    "OS local IANA timezone captured at draw and evaluated at the oracle instant"
)
ZONE_TAB_PATHS = (
    Path("/var/db/timezone/zoneinfo/zone.tab"),
    Path("/usr/share/zoneinfo/zone.tab"),
)
ZONE_ID_PATTERN = re.compile(r"[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def _valid_zone_id_text(value: Any) -> bool:
    parts = value.split("/") if isinstance(value, str) else []
    return (
        isinstance(value, str)
        and 0 < len(value) <= 255
        and not value.startswith(":")
        and not value.startswith("/")
        and all(part not in {"", ".", ".."} for part in parts)
        and ZONE_ID_PATTERN.fullmatch(value) is not None
    )


def _valid_zone_id(value: str | None) -> str | None:
    if not _valid_zone_id_text(value):
        return None
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return value


def os_timezone_id() -> str | None:
    from_environment = _valid_zone_id(os.environ.get("TZ"))
    if from_environment is not None:
        return from_environment

    try:
        target = os.readlink("/etc/localtime")
    except OSError:
        target = ""
    marker = "zoneinfo/"
    if marker in target:
        from_symlink = _valid_zone_id(target.split(marker, 1)[1])
        if from_symlink is not None:
            return from_symlink

    fixed_probe = datetime(2000, 1, 1, tzinfo=timezone.utc)
    local_zone = fixed_probe.astimezone().tzinfo
    return _valid_zone_id(getattr(local_zone, "key", None))


def _parse_coordinate_component(raw: str, degree_digits: int) -> int:
    if not raw or raw[0] not in "+-" or not raw[1:].isdigit():
        raise ValueError("invalid zone.tab coordinate component")
    digits = raw[1:]
    if len(digits) not in {degree_digits + 2, degree_digits + 4}:
        raise ValueError("invalid zone.tab coordinate precision")
    degrees = int(digits[:degree_digits])
    minutes = int(digits[degree_digits : degree_digits + 2])
    seconds = int(digits[degree_digits + 2 :] or "0")
    if minutes >= 60 or seconds >= 60:
        raise ValueError("invalid zone.tab coordinate angle")
    decimal = degrees + minutes / 60 + seconds / 3_600
    if raw[0] == "-":
        decimal = -decimal
    return round(decimal * 1_000_000)


def parse_zone_tab_coordinates(value: str) -> tuple[int, int]:
    if not isinstance(value, str) or len(value) < 2:
        raise ValueError("invalid zone.tab coordinate pair")
    split_at = next(
        (
            index
            for index, character in enumerate(value[1:], start=1)
            if character in "+-"
        ),
        None,
    )
    if split_at is None:
        raise ValueError("invalid zone.tab coordinate pair")
    latitude = _parse_coordinate_component(value[:split_at], 2)
    longitude = _parse_coordinate_component(value[split_at:], 3)
    if not -90_000_000 <= latitude <= 90_000_000:
        raise ValueError("zone.tab latitude is out of range")
    if not -180_000_000 <= longitude <= 180_000_000:
        raise ValueError("zone.tab longitude is out of range")
    return latitude, longitude


def zone_reference(zone_id: str) -> dict[str, Any] | None:
    for path in ZONE_TAB_PATHS:
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        for line in raw.decode("utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) < 3 or fields[2] != zone_id:
                continue
            latitude, longitude = parse_zone_tab_coordinates(fields[1])
            return {
                "source": "OS IANA zone.tab representative point",
                "country_codes": fields[0],
                "coordinate_text": fields[1],
                "latitude_microdegrees": latitude,
                "longitude_microdegrees": longitude,
                "comment": fields[3] if len(fields) > 3 else None,
                "zone_tab_sha256": hashlib.sha256(raw).hexdigest(),
            }
    return None


def uuid7_start_utc(thread_id: str | None) -> datetime | None:
    if not thread_id:
        return None
    try:
        parsed = uuid.UUID(thread_id)
    except (ValueError, AttributeError):
        return None
    if parsed.version != 7:
        return None
    unix_milliseconds = int(parsed.hex[:12], 16)
    try:
        return datetime.fromtimestamp(unix_milliseconds / 1_000, timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _iso_milliseconds(moment: datetime) -> str:
    return moment.isoformat(timespec="milliseconds")


def capture_os_timezone_context(timestamp: str) -> dict[str, Any]:
    moment = _parse_aware_timestamp(timestamp, "oracle-moment")
    timestamp_offset = moment.utcoffset()
    if timestamp_offset is None:
        raise ValueError("oracle-moment timestamp produced no UTC offset")
    zone_id = os_timezone_id()
    if zone_id is None:
        return {
            "available": False,
            "context_version": TIMEZONE_CONTEXT_VERSION,
            "timestamp_utc_offset_seconds": int(timestamp_offset.total_seconds()),
            "reason": "OS IANA timezone identity is unavailable",
        }

    local = moment.astimezone(ZoneInfo(zone_id))
    local_offset = local.utcoffset()
    if local_offset is None:
        raise ValueError("oracle-moment timezone produced no UTC offset")
    return {
        "available": True,
        "context_version": TIMEZONE_CONTEXT_VERSION,
        "timezone_id": zone_id,
        "moment_local": _iso_milliseconds(local),
        "utc_offset_seconds": int(local_offset.total_seconds()),
        "timestamp_utc_offset_seconds": int(timestamp_offset.total_seconds()),
        "source": ORACLE_TIMEZONE_SOURCE,
    }


def capture_thread_origin() -> dict[str, Any]:
    zone_id = os_timezone_id()
    start_utc = uuid7_start_utc(os.environ.get("CODEX_THREAD_ID"))
    if start_utc is None:
        return {
            "available": False,
            "context_version": CONTEXT_VERSION,
            "reason": "CODEX_THREAD_ID is absent or is not UUIDv7",
        }
    if zone_id is None:
        return {
            "available": False,
            "context_version": CONTEXT_VERSION,
            "reason": "OS IANA timezone identity is unavailable",
        }
    reference = zone_reference(zone_id)
    if reference is None:
        return {
            "available": False,
            "context_version": CONTEXT_VERSION,
            "reason": "OS zone.tab has no representative point for the timezone",
        }

    local = start_utc.astimezone(ZoneInfo(zone_id))
    offset = local.utcoffset()
    if offset is None:
        raise ValueError("thread-origin timezone produced no UTC offset")
    return {
        "available": True,
        "context_version": CONTEXT_VERSION,
        "thread_start_utc": _iso_milliseconds(start_utc),
        "thread_start_local": _iso_milliseconds(local),
        "timezone_id": zone_id,
        "utc_offset_seconds": int(offset.total_seconds()),
        "reference_point": reference,
        "start_source": START_SOURCE,
        "timezone_source": TIMEZONE_SOURCE,
    }


def _parse_aware_timestamp(value: Any, label: str) -> datetime:
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {label} timestamp") from exc
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError(f"{label} timestamp must be timezone-aware")
    return moment


def validate_os_timezone_context(value: Any, timestamp: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("oracle-moment timezone context must be an object")
    timestamp_moment = _parse_aware_timestamp(timestamp, "oracle-moment")
    timestamp_offset = timestamp_moment.utcoffset()
    if timestamp_offset is None:
        raise ValueError("oracle-moment timestamp produced no UTC offset")
    expected_timestamp_offset = int(timestamp_offset.total_seconds())

    if value.get("available") is False:
        expected_keys = {
            "available",
            "context_version",
            "timestamp_utc_offset_seconds",
            "reason",
        }
        if (
            set(value) != expected_keys
            or value.get("context_version") != TIMEZONE_CONTEXT_VERSION
            or type(value.get("timestamp_utc_offset_seconds")) is not int
            or value.get("timestamp_utc_offset_seconds") != expected_timestamp_offset
            or not isinstance(value.get("reason"), str)
            or not value["reason"]
        ):
            raise ValueError("invalid unavailable oracle-moment timezone context")
        return value

    expected_keys = {
        "available",
        "context_version",
        "timezone_id",
        "moment_local",
        "utc_offset_seconds",
        "timestamp_utc_offset_seconds",
        "source",
    }
    if (
        set(value) != expected_keys
        or value.get("available") is not True
        or value.get("context_version") != TIMEZONE_CONTEXT_VERSION
        or not _valid_zone_id_text(value.get("timezone_id"))
        or type(value.get("utc_offset_seconds")) is not int
        or type(value.get("timestamp_utc_offset_seconds")) is not int
        or value.get("timestamp_utc_offset_seconds") != expected_timestamp_offset
        or value.get("source") != ORACLE_TIMEZONE_SOURCE
    ):
        raise ValueError("invalid available oracle-moment timezone context")
    local = _parse_aware_timestamp(value["moment_local"], "oracle-moment local")
    local_offset = local.utcoffset()
    if (
        local_offset is None
        or value["utc_offset_seconds"] != int(local_offset.total_seconds())
        or local.astimezone(timezone.utc) != timestamp_moment.astimezone(timezone.utc)
        or _iso_milliseconds(local) != value["moment_local"]
    ):
        raise ValueError("oracle-moment timezone context is internally inconsistent")
    return value


def validate_thread_origin(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("thread origin must be an object")
    if value.get("available") is False:
        if set(value) != {"available", "context_version", "reason"}:
            raise ValueError("invalid unavailable thread-origin shape")
        if value["context_version"] != CONTEXT_VERSION or not isinstance(
            value["reason"], str
        ):
            raise ValueError("invalid unavailable thread-origin values")
        return value

    expected = {
        "available",
        "context_version",
        "thread_start_utc",
        "thread_start_local",
        "timezone_id",
        "utc_offset_seconds",
        "reference_point",
        "start_source",
        "timezone_source",
    }
    if (
        set(value) != expected
        or value.get("available") is not True
        or value.get("context_version") != CONTEXT_VERSION
    ):
        raise ValueError("invalid available thread-origin shape")
    if (
        value["start_source"] != START_SOURCE
        or value["timezone_source"] != TIMEZONE_SOURCE
    ):
        raise ValueError("invalid thread-origin source declaration")
    if not _valid_zone_id_text(value["timezone_id"]):
        raise ValueError("invalid thread-origin timezone")
    start_utc = _parse_aware_timestamp(value["thread_start_utc"], "thread-origin UTC")
    start_local = _parse_aware_timestamp(
        value["thread_start_local"], "thread-origin local"
    )
    if (
        start_utc.utcoffset() != timezone.utc.utcoffset(start_utc)
        or _iso_milliseconds(start_utc) != value["thread_start_utc"]
        or _iso_milliseconds(start_local) != value["thread_start_local"]
        or start_local.astimezone(timezone.utc) != start_utc
    ):
        raise ValueError("thread-origin timestamps are internally inconsistent")
    offset = start_local.utcoffset()
    if (
        type(value["utc_offset_seconds"]) is not int
        or offset is None
        or value["utc_offset_seconds"] != int(offset.total_seconds())
    ):
        raise ValueError("thread-origin UTC offset does not match timezone")

    reference = value["reference_point"]
    reference_keys = {
        "source",
        "country_codes",
        "coordinate_text",
        "latitude_microdegrees",
        "longitude_microdegrees",
        "comment",
        "zone_tab_sha256",
    }
    if not isinstance(reference, dict) or set(reference) != reference_keys:
        raise ValueError("invalid thread-origin reference point")
    if (
        not isinstance(reference["country_codes"], str)
        or not reference["country_codes"]
        or not isinstance(reference["coordinate_text"], str)
        or type(reference["latitude_microdegrees"]) is not int
        or type(reference["longitude_microdegrees"]) is not int
        or reference["comment"] is not None
        and not isinstance(reference["comment"], str)
        or not isinstance(reference["zone_tab_sha256"], str)
        or SHA256_PATTERN.fullmatch(reference["zone_tab_sha256"]) is None
    ):
        raise ValueError("invalid thread-origin reference-point types")
    latitude, longitude = parse_zone_tab_coordinates(reference["coordinate_text"])
    if (
        reference["source"] != "OS IANA zone.tab representative point"
        or reference["latitude_microdegrees"] != latitude
        or reference["longitude_microdegrees"] != longitude
    ):
        raise ValueError("invalid thread-origin reference-point values")
    return value
