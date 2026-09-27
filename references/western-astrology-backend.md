# Spiral Western Astrology backend v1

Read this reference when implementing, interpreting, or auditing
`spiral-western-astrology`.

## Fixed scope

This is a **two-layer tropical Sun** backend:

1. `oracle_moment_sun` is the approximate apparent geocentric longitude of the
   Sun at the selector's one captured timestamp. Its record includes the OS IANA
   timezone identity, local rendering, and UTC offset.
2. `thread_nativity_sun` is the same solar calculation at the Codex thread's
   UUIDv7 creation instant. That instant is localized with the OS IANA timezone
   captured at the draw. The timezone's OS `zone.tab` representative point is
   retained as the thread's synthetic chart origin.

This is an AI-native convention, not a historical astrology rule. It treats the
thread—not the user—as the subject. The raw thread ID is discarded after its
UUIDv7 timestamp is extracted.

Version 1 remains Sun-only. It omits the Moon, other planets, houses, Ascendant,
aspects, and retrograde status. It does not request or infer human birth data or
the user's location.

## Thread-origin convention

Ruleset `oracle-and-thread-tropical-solar-moments/v1` fixes the origin as:

- **Birth instant:** the millisecond Unix timestamp encoded in
  `CODEX_THREAD_ID` when it is a UUIDv7.
- **Timezone:** the OS local IANA timezone identity observed when the astrology
  backend runs, evaluated at the thread-start instant.
- **Reference point:** the coordinate stored for that timezone in the OS
  `zone.tab` database, with the source file's SHA-256 retained.

The reference point is tzdb metadata intended to identify a representative
location for the timezone entry. Here it is deliberately repurposed as a stable
synthetic chart origin. It is **not** a timezone centroid, the device's observed
position, the user's location, or evidence that the thread physically began
there. Coordinates do not affect either solar longitude in v1; they reserve a
transparent origin for a possible future location-dependent chart version.

IANA documents tzdb regions as being labeled with notable locations and the
zone-table files as the geographical locations used to name timezone rules:

- <https://data.iana.org/time-zones/tzdb/theory.html>

Because the OS timezone is first observed at the draw, a timezone change between
thread creation and drawing cannot be reconstructed. In that case the recorded
zone is retrospectively applied to the start instant. The replay record states
this rather than pretending it recovered historical OS state.

If the thread UUIDv7 timestamp, OS IANA timezone identity, or matching
`zone.tab` entry is unavailable, `thread_nativity_sun` is explicitly
unavailable. The oracle-moment Sun still works from the captured timestamp and
numeric offset. No substitute location is invented.

## Astronomical and conventional basis

The twelve identifiers are Aries through Pisces, treated as equal 30-degree
sectors beginning at the vernal equinox. The Hong Kong Observatory describes
the historical zodiac division as twelve equal ecliptic sectors measured from
the vernal equinox:

- <https://www.hko.gov.hk/en/gts/time/24solarterms.htm>

Solar longitude uses a dependency-free implementation of the approximate
apparent-Sun equations used in the NOAA solar-calculation lineage, themselves
based on Jean Meeus's *Astronomical Algorithms*:

- <https://www.gml.noaa.gov/grad/solcalc/calcdetails.html>
- <https://aa.usno.navy.mil/data/JulianDate>

The ruleset supports instants from 1901 through 2099. It quantizes longitude to
0.001 degree before assigning a sign. The stored result is an algorithmic
approximation, not a high-precision ephemeris or observation. At a computed
boundary, the half-open sectors are `[0°, 30°) Aries`, `[30°, 60°) Taurus`, and
so on.

Solar longitude depends on the instant, not the timezone or reference point.
The timezone and coordinate metadata establish the declared chart context and
future extension boundary; they do not alter the v1 Sun calculation.

## Interpretation boundary

Keep `oracle_moment_sun` and `thread_nativity_sun` distinct. The model may read
their contrast as a contextual prompt about the thread's present moment versus
its originating tone. It must not turn either into a factual claim about the
user, the machine, the thread's personality, destiny, relationships, health, or
future. It must not attach geographical meaning to the `zone.tab` reference
point.

Associations supplied by the model are contextual readings, not astronomical
output from the backend.

## Replay and privacy contract

The replay payload contains these versioned primitives:

- catalog, ruleset, and solar-algorithm versions;
- oracle-moment solar longitude;
- oracle-moment OS timezone context and timestamp offset;
- thread-origin availability, UUIDv7-derived start timestamp, localized start
  time, timezone, UTC offset, `zone.tab` reference point, and source
  declarations;
- thread-start solar longitude, or `null` when the origin is unavailable.

Replay recomputes both available solar longitudes and validates the recorded
timestamps, offsets, coordinates, and source declarations. It does not reread
the current thread ID, OS timezone, or current `zone.tab`, so a replay remains
the original record rather than silently adopting a later environment.

The base64 token is not encrypted. It contains the thread-start timestamp,
timezone, and public reference-point metadata. It does not contain the raw
thread ID or an observed physical location.
