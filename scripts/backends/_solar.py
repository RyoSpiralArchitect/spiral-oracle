"""Shared, versioned solar-longitude calculations for time-based backends."""

from __future__ import annotations

import math
from datetime import datetime, timezone


ALGORITHM_VERSION = "meeus-noaa-apparent-sun/v1"
MIN_SUPPORTED_YEAR = 1901
MAX_SUPPORTED_YEAR = 2099
MILLIDEGREES_PER_CIRCLE = 360_000


def parse_moment(timestamp: str) -> datetime:
    if not isinstance(timestamp, str):
        raise ValueError("timestamp must be timezone-aware ISO 8601 text")
    try:
        moment = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError("timestamp must be valid ISO 8601 text") from exc
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    if not MIN_SUPPORTED_YEAR <= moment.year <= MAX_SUPPORTED_YEAR:
        raise ValueError(
            f"time-derived backends support years {MIN_SUPPORTED_YEAR} through "
            f"{MAX_SUPPORTED_YEAR}"
        )
    return moment


def julian_day_utc(moment: datetime) -> float:
    utc = moment.astimezone(timezone.utc)
    year = utc.year
    month = utc.month
    if month <= 2:
        year -= 1
        month += 12
    century = year // 100
    correction = 2 - century + century // 4
    day_fraction = (
        utc.hour
        + utc.minute / 60
        + utc.second / 3_600
        + utc.microsecond / 3_600_000_000
    ) / 24
    return (
        math.floor(365.25 * (year + 4_716))
        + math.floor(30.6001 * (month + 1))
        + utc.day
        + correction
        - 1_524.5
        + day_fraction
    )


def apparent_solar_longitude_millidegrees(timestamp: str) -> int:
    """Approximate geocentric apparent solar longitude, tropical, of date."""

    moment = parse_moment(timestamp)
    centuries = (julian_day_utc(moment) - 2_451_545.0) / 36_525
    mean_longitude = (
        280.46646 + centuries * (36_000.76983 + 0.0003032 * centuries)
    ) % 360
    mean_anomaly = math.radians(
        357.52911 + centuries * (35_999.05029 - 0.0001537 * centuries)
    )
    equation_of_center = (
        math.sin(mean_anomaly)
        * (1.914602 - centuries * (0.004817 + 0.000014 * centuries))
        + math.sin(2 * mean_anomaly) * (0.019993 - 0.000101 * centuries)
        + math.sin(3 * mean_anomaly) * 0.000289
    )
    omega = math.radians(125.04 - 1_934.136 * centuries)
    apparent_longitude = (
        mean_longitude + equation_of_center - 0.00569 - 0.00478 * math.sin(omega)
    ) % 360
    quantized = round(apparent_longitude * 1_000)
    return quantized % MILLIDEGREES_PER_CIRCLE


def utc_offset_seconds(moment: datetime) -> int:
    offset = moment.utcoffset()
    if offset is None:
        raise ValueError("timestamp must include a UTC offset")
    seconds = offset.total_seconds()
    if not seconds.is_integer():
        raise ValueError("UTC offset must resolve to whole seconds")
    return int(seconds)
