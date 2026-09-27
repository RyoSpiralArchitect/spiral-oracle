# Spiral Four Pillars backend v1

Read this reference when implementing, interpreting, or auditing
`spiral-four-pillars`.

## Fixed scope

This backend derives year, month, day, and hour pillars for the **oracle
moment**. It is not a natal chart and does not request or retain birth time,
birthplace, latitude, or longitude.

The selector captures the OS-local timezone-aware timestamp once. Version 1
uses its civil date, clock time, and fixed UTC offset. Replay stores that offset
inside the timestamp, so later OS timezone or daylight-saving changes do not
change the result. A timezone offset is not treated as a geographical location.

## Source-attested structure

The Hong Kong Observatory documents the ten Heavenly Stems, twelve Earthly
Branches, 60-pair Gan-Zhi cycle, twelve two-hour `shichen`, month-stem table,
hour-stem table, and the use of the four Gan-Zhi pairs as the Eight Characters:

- <https://www.hko.gov.hk/en/gts/time/stemsandbranches.htm>

It also documents the 24 solar terms as 15-degree divisions of solar longitude,
including Spring Commences at 315 degrees:

- <https://www.hko.gov.hk/en/gts/time/24solarterms.htm>

The Observatory explicitly notes that fortune-telling practice often changes
the Gan-Zhi year at Spring Commences, while the official civil Chinese calendar
uses Lunar New Year. This backend selects the former convention because its
scope is Four Pillars, not civil-calendar conversion:

- <https://www.hko.gov.hk/en/education/astronomy-and-time/time-service/00506-what-year-is-it-today.html>

The U.S. Naval Observatory's *Explanatory Supplement to the Astronomical
Almanac* supplies independent descriptions of the 60-cycle, solar terms, Julian
day numbering, and midnight-to-midnight modern calendar days:

- <https://aa.usno.navy.mil/downloads/c15_usb_online.pdf>

## Spiral ruleset

Ruleset `li-chun-jie-civil-midnight/v1` fixes these choices:

- Supported timestamp years: 1901 through 2099.
- Year boundary: computed solar longitude 315 degrees (`Li Chun`).
- Month boundaries: twelve 30-degree `Jie` sectors, beginning with Yin at 315
  degrees, then Mao at 345, Chen at 15, and so on.
- Solar longitude: the same approximate, 0.001-degree-quantized algorithm used
  by the Western astrology backend.
- Day: proleptic Gregorian local civil date; its sexagenary index is
  `(civil JDN + 49) mod 60`.
- Day boundary: local civil midnight. Some Four Pillars schools advance the day
  at 23:00; this backend does not.
- Hour branch: Zi is 23:00 through 00:59, Chou is 01:00 through 02:59, and so on.
- Month stems follow the year-stem table; hour stems follow the day-stem table.
- No true-solar-time or longitude correction is applied.

The modern-date fixtures are checked against official almanac surfaces. For
2026-08-29, the Hong Kong Observatory lists Bing-Wu year and Yi-Hai day, while
its monthly/Korean Astronomy and Space Science Institute calendar surfaces list
the Bing-Shen month:

- <https://www.hko.gov.hk/en/gts/astron2026/files/HKO_almanac_2026.pdf>
- <https://astro.kasi.re.kr/kor/life/pageView/5>

These choices are versioned conventions, not a claim that all Four Pillars
lineages use identical year, day, timezone, or solar-time boundaries.

## Interpretation boundary

Keep the four returned pairs intact before looking for tensions, repetitions,
or contrasts. Do not calculate hidden stems, luck pillars, ten gods, strength,
favorable elements, compatibility, health, personality, fate, or predictions:
none of those are backend outputs in v1. Any association supplied by the model
must be identified as a contextual reading of the oracle moment.

## Replay contract

The replay payload contains exactly the version fields plus:

- `solar_longitude_millidegrees`
- `local_civil_date`
- `local_hour_zero_based`
- `utc_offset_seconds`

Replay recomputes every field from the top-level timestamp and rejects a
mismatch. It consumes no fresh randomness; randomness has already occurred in
the backend selector.
