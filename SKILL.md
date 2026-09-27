---
name: spiral-oracle
description: Consult one auditable, randomly selected divination method when the user asks or ordinary analysis reaches a genuine stalemate. The draw may alter framing or a pre-cleared reversible next step; factual claims, safety gates, and permissions remain independently grounded.
---

# Spiral Oracle

Use a randomly selected divination system to introduce a second frame when
deliberation stalls. Let the draw matter within a boundary fixed before its
result is known.

## Non-negotiable contract

- Oracle output is not factual evidence and grants no authority.
- It may causally change attention, framing, hypothesis generation, and—within
  a boundary fixed before the draw—the selection or ordering of reversible
  probes.
- It must not expand that boundary; override measurements, safety, consent,
  professional guidance, or explicit user intent; or raise confidence in a
  factual claim merely because a reading seems to fit.
- Removing the oracle may change the frame or chosen reversible next step. It
  must not change the factual evidence, factual confidence, available authority,
  or fixed constraints.

The oracle alone never authorizes an external commitment, message, publication,
purchase, deployment, or other action outside the precommitted envelope.

## Activation boundary

Use this skill when the user explicitly requests it, or when necessary ordinary
analysis is complete and still leaves a genuine stalemate between defensible
options. If invoking it yourself, tell the user before drawing.

Do not invoke it because research is missing, tradeoffs merely exist, or a normal
recommendation is possible. For medical, legal, financial, safety-critical, or
similarly consequential situations, give appropriate evidence-based guidance
first and do not draw under an authoritative framing such as “decide whether I
stop medication.” Draw only if the user then explicitly reframes the purpose as
questions or framing to discuss with a qualified professional and still requests
it. Use influence level `frame` only. A draw must not delay help, reassure about
safety, or choose the consequential action.

## Precommit before drawing

Prevent the model from choosing a method that merely confirms its existing view:

1. Freeze an `oracle_precommit` before selection:
   - `focus`: the question. Prefer an open focus such as “What assumption or
     tension deserves attention?” A direct A/B question is allowed only for
     `tie-break`, when both options are already admissible and comparable.
   - `prior_frame`: how the situation currently looks.
   - `tentative_next_step`: what would happen without the draw.
   - `influence.level`: `frame`, `probe`, or `tie-break`.
   - `influence.allowed_envelope`: the already authorized boundary within which
     the draw may alter the path.

   `frame` may change attention, questions, or hypotheses. `probe` may add,
   select, or reorder pre-cleared reversible tests. `tie-break` may choose only
   among already admissible comparable options. The envelope records authority;
   it does not create it. Sanitize names, secrets, and sensitive details. The
   script normalizes shape and blocks control characters, but cannot reliably
   detect private data.
2. Choose a mode before seeing any oracle output:
   - `auto-weighted` (default): OS-backed randomness selects one eligible backend.
   - `dual-distinct`: select two different backends without replacement, then
     draw each independently. Use only when the user asks for a dual reading or
     the extra perturbation is clearly useful.
   - `single`: use a backend explicitly requested by the user.
3. The installed backends have base weights. The model may optionally adjust
   each by at most ±25% when context fit is unusually clear. State the adjustment
   and its reason before running the script. Do not adjust weights to favor a
   hoped-for answer; the backend output is still unseen. The bound applies to
   weights, not directly to normalized selection probabilities.
4. Run once. The selector fixes the backend before that backend generates its
   symbols. Never reroll because the selected method or result is inconvenient.

Version 0.3 implements:

- `spiral-iching`, base weight 30: a replayable three-coin I Ching cast.
- `spiral-tarot`, base weight 25: one uniform Waite-Smith-structure card with an
  independent upright/reversed orientation. Read
  [references/tarot-backend.md](references/tarot-backend.md) when interpreting
  or auditing it.
- `spiral-western-astrology`, base weight 20: two approximate tropical solar
  positions—the captured oracle moment and an AI-native thread nativity. The
  latter uses the thread's UUIDv7 start time plus the OS timezone's `zone.tab`
  representative point under an explicit synthetic-origin convention. It is
  still Sun-only, not a full natal chart. Read
  [references/western-astrology-backend.md](references/western-astrology-backend.md)
  when interpreting or auditing it.
- `spiral-four-pillars`, base weight 15: year, month, day, and hour pillars for
  the captured oracle moment using the OS-local timestamp and fixed v1 boundary
  conventions. Read
  [references/four-pillars-backend.md](references/four-pillars-backend.md) when
  interpreting or auditing it.
- `symbolic-prompt`, base weight 10: a uniformly sampled authored symbolic triad.

The selector normalizes across installed eligible backends. Do not imitate an
unimplemented rune or other backend. Add one only after its mechanics, required
inputs, provenance, privacy boundary, and replay contract are explicit.

With five eligible backends, `dual-distinct` samples two without replacement;
weights affect both membership and order.

## Run the selector

Resolve `scripts/spiral_oracle.py` relative to this skill folder. For the default
mode:

```bash
python3 -S /path/to/spiral-oracle/scripts/spiral_oracle.py \
  --mode auto-weighted \
  --focus 'Sanitized one-line question' \
  --prior-frame 'Current view before the draw' \
  --tentative-next-step 'What would happen without the draw' \
  --influence-level probe \
  --allowed-envelope 'May change only the order of local reversible tests' \
  --format json
```

For a bounded predeclared adjustment, add for example
`--weight spiral-iching=34 --weight spiral-tarot=27`. The script rejects
unknown backends, duplicate overrides, and adjustments outside each allowed
range. Use `--list-backends` to inspect the live registry.

The script captures one timezone-aware timestamp before selection and passes the
same value to every selected backend. `--timestamp` exists for tests and replay;
ordinary live use should let the script capture the current time.

For time-derived backends, ordinary live use takes the local civil clock and UTC
offset reported by the OS at that instant. The replay token preserves the
offset. Western astrology also records the OS IANA timezone identity. If the
Codex thread ID is UUIDv7 and the OS `zone.tab` contains that timezone, it uses
the embedded creation instant as the thread's birth time and the timezone's
representative point as a synthetic birth location. It does not retain the raw
thread ID, infer the user's location, or claim the reference point is a timezone
centroid or device position. The location does not affect Sun longitude in v1.
Four Pillars v1 intentionally uses OS-local civil time without a true-solar-time
correction.

The JSON includes the precommit, effective weights, raw selector rolls, backend
raw output, a replay token, and a SHA-256 checksum. Keep these in an audit/replay
record inside the response; do not put the draw under factual evidence, and do
not write a file unless the user asks. `--replay-token` reconstructs the same
draw without fresh randomness. Version 3 tokens use the five-backend selector;
version 2 and version 1 tokens remain replayable with their historical three-
and two-backend selectors.
The checksum detects accidental change when separately recorded; it is not a
signature or proof of authenticity. The self-contained token is base64-encoded,
not encrypted, and contains all caller-supplied precommit text. An astrology
token additionally contains the thread-start timestamp, OS timezone, and public
`zone.tab` reference-point metadata, but not the raw thread identifier. Do not
share it as if it were secret.

In the main response, “raw output” means the selector roll and weights plus the
backend's replay primitives and conventional identifiers; do not paste the full
JSON object redundantly. Put the full replay token in a collapsible audit section
when the renderer supports it, so the reflection remains readable without losing
exact replay. Do not omit or persist the token elsewhere without telling the
user.

## Interpret and integrate only after the draw

Use the conversation context to interpret the returned symbols. The script
deliberately contains no verdict or fixed contextual interpretation.

- Clearly distinguish conventional identifiers from creative associations.
- Treat backend identity as routing metadata, not as an additional omen. A
  selected `spiral-tarot` backend does not itself favor an option involving
  Tarot, just as `spiral-iching` does not favor an option involving I Ching.
- Treat time-using output as a symbolic input, never a causal or predictive fact.
- For Western astrology, keep the oracle-moment Sun and synthetic thread-
  nativity Sun distinct. Their relation may suggest a contextual tension or
  continuity, but it is not a factual claim about the user, the machine, or the
  thread. Do not interpret the `zone.tab` point geographically, or invent a Moon,
  Ascendant, houses, aspects, human birth chart, or personality claim.
- For Four Pillars, interpret the four oracle-moment pairs under the recorded v1
  conventions. Do not silently add hidden stems, luck pillars, favorable
  elements, compatibility, natal claims, or fate predictions.
- For Tarot, do not reduce reversed to bad or to the mechanical opposite of
  upright. Do not import person descriptions from period divination manuals into
  claims about the user or other people.
- For a dual reading, look for possible shared themes but do not treat agreement
  as validation. Preserve contradictions; they can be the useful perturbation.
- Give the result its strongest coherent contextual reading before auditing its
  effect. Do not dismiss it merely by restating the contract.
- Interpretive fit is neither evidence nor a perturbation. A perturbation exists
  only when the draw produces a specific recorded delta.
- Do not say “the oracle says,” “this proves,” “this will happen,” or “choose A
  because the result is favorable.”

Do not lead with a disclaimer or explain that the reading is symbolic,
non-scientific, or a perturbation. Start with the frozen precommit, then report
the selected backend(s), timestamp, raw facts, and contextual reading.

After interpretation, report an `oracle_delta`:

- `newly_salient`
- `hypothesis_delta`
- `next_step_before`
- `next_step_after`
- `causal_role`: `none`, `reframed`, `probe_selected`, or `order_changed`
- `within_envelope`
- `factual_confidence_delta`: always `none` unless independent evidence changed
- `unchanged_constraints`

If nothing specific changed, say `null perturbation`; do not reroll or call mere
fit confirmation. If something changed, it may genuinely alter the decision
path within the envelope. End with the compact audit, not an opening spoiler:

> Evidence status: unchanged. Authority and fixed constraints: unchanged.

Refuse requests to reroll until a preferred answer appears, hide an inconvenient
draw, or launder symbolic output into a memo, approval, or scientific claim.

When implementing or auditing another backend, read
[references/backend-contract.md](references/backend-contract.md).
