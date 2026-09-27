# Spiral Oracle backend contract

Read this reference only when adding, changing, or auditing a backend.

## Purpose

A backend produces raw divination structure after the selector has fixed the
method. It does not interpret the user's situation, recommend an action, or claim
epistemic authority. The orchestrator owns selection, precommit capture,
timestamp capture, replay packaging, and the factual/authority boundary.

## Python module interface

Register a module in `scripts/backends/__init__.py`. It must expose:

```python
BACKEND_ID: str
DISPLAY_NAME: str
BASE_WEIGHT: int
USES_TIMESTAMP: bool
REQUIRED_INPUTS: tuple[str, ...]
BACKEND_SCHEMA: str
REPLAY_SCHEMA: str

def generate(timestamp: str) -> tuple[dict, dict]:
    """Return (public_result, replay_payload) using fresh OS-backed randomness."""

def replay(payload: dict, timestamp: str) -> dict:
    """Validate payload and reconstruct exactly the same public_result."""
```

Backend identifiers use lowercase letters, digits, and hyphens. Base weights are
positive integers. Results and replay payloads must be JSON-serializable.

## Invariants

- Validate the imported Python API as strictly as the CLI. Never assume replay
  payloads are trusted merely because the orchestrator produced them.
- `generate` uses OS-backed randomness, not timestamps, hashes of the question,
  or model-selected pseudo-random values, unless the backend's named historical
  method explicitly defines another source.
- `replay` consumes no fresh randomness and is deterministic for the same
  payload and timestamp.
- Put raw draws, orientations, ordering, and transformations in `public_result`.
  Preserve enough in `replay_payload` to reconstruct it exactly.
- Include the exact `REPLAY_SCHEMA` and any catalog or ruleset version in every
  replay payload. Reject older or unknown versions rather than interpreting them
  with current tables.
- Do not bundle contextual readings, favorable/unfavorable scores, predictions,
  recommendations, or external side effects.
- If a finite authored vocabulary is sampled, disclose that authorship. Random
  selection does not make the vocabulary neutral or exhaustive.
- Use the single timestamp supplied by the orchestrator. Do not capture another
  “now” inside a backend.
- If a backend reads environment metadata such as an OS timezone or thread
  creation identifier, minimize it into explicit versioned replay primitives.
  Replay must validate those recorded primitives without rereading or requiring
  the original environment.

## Eligibility and sensitive inputs

`REQUIRED_INPUTS` declares inputs beyond the timestamp. The current selector
registers only backends whose required inputs are empty. A future backend must
remain ineligible until the orchestrator can explicitly obtain, validate, and
audit all of its required inputs.

Do not treat a label such as “astrology” or “Four Pillars” as a sufficiently
specified algorithm. Any new or revised time-derived backend must fix the exact
school/method, timezone rules, location requirements, calendar or ephemeris
source, boundary behavior, and replay representation. The current v1 choices
are recorded in `western-astrology-backend.md` and `four-pillars-backend.md`.
Human birth time, birthplace, and precise location are sensitive data: require
an explicit user request and minimize retention. The Western astrology backend's
thread origin is synthetic metadata about the Codex thread and OS timezone; it
must never be relabeled as the user's birthplace or physical location.

## Tests required for a new backend

Run the persistent suite from the skill folder:

```bash
python3 -S -m unittest discover -s scripts/tests -p 'test_*.py'
```

- Fixed replay fixtures reconstruct byte-equivalent public results.
- Invalid and out-of-range replay fields fail closed.
- Ordering and transformation conventions have named reference fixtures.
- Random draws reach only declared values and follow the intended distribution.
- The result contains no contextual recommendation or decision field.
- One top-level timestamp is propagated unchanged.

After registration, give the new selector registry its own immutable version.
Test selector coverage, bounded weight validation, `dual-distinct` uniqueness,
new replay-token round trips, historical replay compatibility, and skill
behavior on both low-stakes and high-stakes prompts.
