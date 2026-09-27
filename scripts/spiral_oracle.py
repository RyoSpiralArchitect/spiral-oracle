#!/usr/bin/env -S python3 -S
"""Auditable divination-backend selector for Spiral Oracle."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import re
import secrets
import sys
import unicodedata
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Sequence

from backends import BACKENDS


SCHEMA_VERSION = "spiral-oracle/v3"
REPLAY_SCHEMA = "spiral-oracle.replay/v3"
PREVIOUS_REPLAY_SCHEMA = "spiral-oracle.replay/v2"
LEGACY_REPLAY_SCHEMA = "spiral-oracle.replay/v1"
SELECTOR_SPEC_V1 = "spiral-oracle.selector/v1"
SELECTOR_SPEC_V2 = "spiral-oracle.selector/v2"
SELECTOR_SPEC_V3 = "spiral-oracle.selector/v3"
CURRENT_SELECTOR_SPEC = SELECTOR_SPEC_V3
SELECTOR_SPECS = MappingProxyType(
    {
        SELECTOR_SPEC_V1: MappingProxyType(
            {
                "spiral-iching": 30,
                "symbolic-prompt": 10,
            }
        ),
        SELECTOR_SPEC_V2: MappingProxyType(
            {
                "spiral-iching": 30,
                "spiral-tarot": 25,
                "symbolic-prompt": 10,
            }
        ),
        SELECTOR_SPEC_V3: MappingProxyType(
            {
                "spiral-iching": 30,
                "spiral-tarot": 25,
                "spiral-western-astrology": 20,
                "spiral-four-pillars": 15,
                "symbolic-prompt": 10,
            }
        ),
    }
)
REPLAY_SELECTOR_SPECS = MappingProxyType(
    {
        LEGACY_REPLAY_SCHEMA: SELECTOR_SPEC_V1,
        PREVIOUS_REPLAY_SCHEMA: SELECTOR_SPEC_V2,
        REPLAY_SCHEMA: SELECTOR_SPEC_V3,
    }
)
PRECOMMIT_REPLAY_SCHEMAS = frozenset({PREVIOUS_REPLAY_SCHEMA, REPLAY_SCHEMA})
MODES = ("auto-weighted", "dual-distinct", "single")
INFLUENCE_LEVELS = ("frame", "probe", "tie-break")
PRECOMMIT_SCHEMA = "spiral-oracle.precommit/v1"
MAX_FOCUS_LENGTH = 240
MAX_FOCUS_BYTES = 1_024
MAX_PRECOMMIT_FIELD_LENGTH = 480
MAX_PRECOMMIT_FIELD_BYTES = 2_048
MAX_REPLAY_TOKEN_LENGTH = 100_000

ORACLE_CONTRACT = {
    "is_factual_evidence": False,
    "grants_authority_or_permission": False,
    "permitted_causal_roles": [
        "change attention or framing",
        "generate hypotheses",
        "select or order pre-cleared reversible probes",
        "break a tie among already admissible comparable options",
    ],
    "may_expand_precommitted_envelope": False,
    "may_override_measurements_safety_consent_or_user_intent": False,
    "interpretive_fit_changes_factual_confidence": False,
    "record_counterfactual_delta": True,
}


def validate_registry() -> None:
    if not BACKENDS:
        raise RuntimeError("no Spiral Oracle backends are registered")
    for backend_id, module in BACKENDS.items():
        if backend_id != module.BACKEND_ID:
            raise RuntimeError(f"backend registry key mismatch: {backend_id}")
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", backend_id) is None:
            raise RuntimeError(f"invalid backend identifier: {backend_id}")
        if type(module.BASE_WEIGHT) is not int or module.BASE_WEIGHT <= 0:
            raise RuntimeError(f"invalid base weight for {backend_id}")
        if not isinstance(module.REQUIRED_INPUTS, tuple):
            raise RuntimeError(f"invalid REQUIRED_INPUTS for {backend_id}")
        if not isinstance(module.BACKEND_SCHEMA, str) or not isinstance(
            module.REPLAY_SCHEMA, str
        ):
            raise RuntimeError(f"missing backend schema version for {backend_id}")
    current_spec = SELECTOR_SPECS[CURRENT_SELECTOR_SPEC]
    registry_weights = {
        backend_id: BACKENDS[backend_id].BASE_WEIGHT
        for backend_id in eligible_backend_ids()
    }
    if registry_weights != current_spec:
        raise RuntimeError(
            "eligible backend registry does not match current selector spec"
        )


def eligible_backend_ids() -> list[str]:
    return [
        backend_id
        for backend_id, module in BACKENDS.items()
        if not module.REQUIRED_INPUTS
    ]


def allowed_weight_range(base_weight: int) -> tuple[int, int]:
    lower = (base_weight * 3 + 3) // 4
    upper = (base_weight * 5) // 4
    return lower, upper


def parse_weight_override(value: str) -> tuple[str, int]:
    backend_id, separator, raw_weight = value.partition("=")
    if not separator or not backend_id or not raw_weight:
        raise argparse.ArgumentTypeError("weights must use BACKEND=INTEGER")
    try:
        weight = int(raw_weight)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("weights must use BACKEND=INTEGER") from exc
    return backend_id, weight


def build_effective_weights(
    overrides: Sequence[tuple[str, int]],
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    weights = dict(SELECTOR_SPECS[CURRENT_SELECTOR_SPEC])
    ranges = {
        backend_id: dict(
            zip(("minimum", "maximum"), allowed_weight_range(weights[backend_id]))
        )
        for backend_id in weights
    }

    seen = set()
    for override in overrides:
        if not isinstance(override, (list, tuple)) or len(override) != 2:
            raise ValueError("each weight override must be a BACKEND, INTEGER pair")
        backend_id, weight = override
        if not isinstance(backend_id, str) or type(weight) is not int:
            raise ValueError("each weight override must be a BACKEND, INTEGER pair")
        if backend_id in seen:
            raise ValueError(f"duplicate weight override for {backend_id}")
        seen.add(backend_id)
        if backend_id not in weights:
            raise ValueError(f"unknown or ineligible backend: {backend_id}")
        minimum = ranges[backend_id]["minimum"]
        maximum = ranges[backend_id]["maximum"]
        if not minimum <= weight <= maximum:
            raise ValueError(
                f"weight for {backend_id} must be between {minimum} and {maximum}"
            )
        weights[backend_id] = weight
    return weights, ranges


def validate_effective_weights(value: Any, selector_spec: str) -> dict[str, int]:
    if selector_spec not in SELECTOR_SPECS:
        raise ValueError("unknown replay selector spec")
    base_weights = SELECTOR_SPECS[selector_spec]
    if not isinstance(value, dict) or set(value) != set(base_weights):
        raise ValueError("replay weights do not match their selector spec")
    # The selector specification, not caller-controlled JSON member order, fixes
    # the weighted intervals. Rebuild in that declared order before selection.
    weights: dict[str, int] = {}
    for backend_id in base_weights:
        weight = value[backend_id]
        minimum, maximum = allowed_weight_range(base_weights[backend_id])
        if type(weight) is not int or not minimum <= weight <= maximum:
            raise ValueError(f"invalid replay weight for {backend_id}")
        weights[backend_id] = weight
    return weights


def normalize_text_field(
    name: str,
    value: Any,
    *,
    maximum_length: int,
    maximum_bytes: int,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be text")
    normalized = unicodedata.normalize("NFC", value)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    if len(normalized) > maximum_length:
        raise ValueError(f"{name} must be at most {maximum_length} characters")
    if len(normalized.encode("utf-8")) > maximum_bytes:
        raise ValueError(f"{name} must be at most {maximum_bytes} UTF-8 bytes")
    if any(
        unicodedata.category(character) in {"Cc", "Cf", "Cs"}
        for character in normalized
    ):
        raise ValueError(
            f"{name} must not contain control, format, or surrogate characters"
        )
    return normalized


def normalize_focus(value: Any) -> str:
    return normalize_text_field(
        "focus",
        value,
        maximum_length=MAX_FOCUS_LENGTH,
        maximum_bytes=MAX_FOCUS_BYTES,
    )


def normalize_precommit_field(name: str, value: Any) -> str:
    return normalize_text_field(
        name,
        value,
        maximum_length=MAX_PRECOMMIT_FIELD_LENGTH,
        maximum_bytes=MAX_PRECOMMIT_FIELD_BYTES,
    )


def normalize_precommit(
    *,
    focus: Any,
    prior_frame: Any,
    tentative_next_step: Any,
    influence_level: Any,
    allowed_envelope: Any,
) -> dict[str, Any]:
    if influence_level not in INFLUENCE_LEVELS:
        choices = ", ".join(INFLUENCE_LEVELS)
        raise ValueError(f"influence level must be one of: {choices}")
    return {
        "schema": PRECOMMIT_SCHEMA,
        "focus": normalize_focus(focus),
        "prior_frame": normalize_precommit_field("prior frame", prior_frame),
        "tentative_next_step": normalize_precommit_field(
            "tentative next step", tentative_next_step
        ),
        "influence": {
            "level": influence_level,
            "allowed_envelope": normalize_precommit_field(
                "allowed envelope", allowed_envelope
            ),
        },
    }


def validate_precommit_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "focus",
        "prior_frame",
        "tentative_next_step",
        "influence",
    }:
        raise ValueError("invalid replay precommit shape")
    if value["schema"] != PRECOMMIT_SCHEMA:
        raise ValueError("unsupported replay precommit schema")
    influence = value["influence"]
    if not isinstance(influence, dict) or set(influence) != {
        "level",
        "allowed_envelope",
    }:
        raise ValueError("invalid replay influence shape")
    normalized = normalize_precommit(
        focus=value["focus"],
        prior_frame=value["prior_frame"],
        tentative_next_step=value["tentative_next_step"],
        influence_level=influence["level"],
        allowed_envelope=influence["allowed_envelope"],
    )
    if normalized != value:
        raise ValueError("replay precommit is not canonical")
    return normalized


def parse_timestamp(value: str | None) -> tuple[str, dict[str, str]]:
    if value is None:
        moment = datetime.now().astimezone()
    else:
        if not isinstance(value, str):
            raise ValueError("timestamp must be ISO 8601 text")
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            moment = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("timestamp must be valid ISO 8601") from exc
        if moment.tzinfo is None or moment.utcoffset() is None:
            raise ValueError("timestamp must include a UTC offset or Z")

    local_iso = moment.isoformat(timespec="milliseconds")
    utc_iso = moment.astimezone(timezone.utc).isoformat(timespec="milliseconds")
    offset = moment.strftime("%z")
    formatted_offset = f"{offset[:3]}:{offset[3:]}" if offset else "unknown"
    return local_iso, {
        "captured_at": local_iso,
        "captured_at_utc": utc_iso,
        "utc_offset": formatted_offset,
        "timezone_identity_preserved": False,
    }


def validate_live_request(
    mode: str,
    explicit_backend: str | None,
    overrides: Sequence[tuple[str, int]],
) -> None:
    if mode not in MODES:
        raise ValueError(f"unknown selector mode: {mode}")
    if mode == "single":
        if explicit_backend is None:
            raise ValueError("single mode requires an eligible backend")
        if overrides:
            raise ValueError("weight overrides are not meaningful in single mode")
    elif explicit_backend is not None:
        raise ValueError("an explicit backend is only valid in single mode")


def weighted_pick(
    candidates: Sequence[str],
    weights: dict[str, int],
    supplied_roll: int | None = None,
) -> tuple[str, dict[str, Any]]:
    if not candidates:
        raise ValueError("weighted selection requires at least one candidate")
    total_weight = sum(weights[backend_id] for backend_id in candidates)
    if supplied_roll is None:
        roll = secrets.randbelow(total_weight)
    else:
        if type(supplied_roll) is not int or not 0 <= supplied_roll < total_weight:
            raise ValueError("selector roll is outside its recorded weight interval")
        roll = supplied_roll

    cursor = 0
    selected = candidates[-1]
    for backend_id in candidates:
        cursor += weights[backend_id]
        if roll < cursor:
            selected = backend_id
            break

    step = {
        "candidates": [
            {
                "backend": backend_id,
                "weight": weights[backend_id],
                "selection_probability": f"{weights[backend_id]}/{total_weight}",
            }
            for backend_id in candidates
        ],
        "total_weight": total_weight,
        "roll_zero_based": roll,
        "selected_backend": selected,
    }
    return selected, step


def select_backends(
    mode: str,
    weights: dict[str, int],
    *,
    explicit_backend: str | None = None,
    supplied_rolls: Sequence[int] | None = None,
) -> tuple[list[str], list[dict[str, Any]], list[int]]:
    candidates = list(weights)
    if mode not in MODES:
        raise ValueError(f"unknown selector mode: {mode}")

    if mode == "single":
        if explicit_backend not in candidates:
            raise ValueError("single mode requires an eligible --backend")
        if supplied_rolls not in (None, []):
            raise ValueError("single mode replay must not contain selector rolls")
        step = {
            "candidates": [{"backend": explicit_backend, "weight": None}],
            "total_weight": None,
            "roll_zero_based": None,
            "selected_backend": explicit_backend,
        }
        return [explicit_backend], [step], []

    required_rolls = 1 if mode == "auto-weighted" else 2
    if mode == "dual-distinct" and len(candidates) < 2:
        raise ValueError("dual-distinct mode requires at least two eligible backends")
    if supplied_rolls is not None and len(supplied_rolls) != required_rolls:
        raise ValueError(
            f"{mode} replay requires exactly {required_rolls} selector rolls"
        )

    selected: list[str] = []
    steps: list[dict[str, Any]] = []
    rolls: list[int] = []
    available = candidates[:]
    for index in range(required_rolls):
        supplied = None if supplied_rolls is None else supplied_rolls[index]
        backend_id, step = weighted_pick(available, weights, supplied)
        selected.append(backend_id)
        steps.append(step)
        rolls.append(step["roll_zero_based"])
        if mode == "dual-distinct":
            available.remove(backend_id)
    return selected, steps, rolls


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def encode_replay_token(payload: dict[str, Any]) -> tuple[str, str]:
    encoded = canonical_json(payload)
    token = base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")
    checksum = hashlib.sha256(encoded).hexdigest()
    return token, checksum


def selection_receipt_sha256(
    *,
    timestamp: str,
    mode: str,
    weights: dict[str, int],
    explicit_backend: str | None,
    rolls: list[int],
    selected_backends: list[str],
    focus: str | None = None,
    precommit: dict[str, Any] | None = None,
    selector_spec: str | None = None,
) -> str:
    if (focus is None) == (precommit is None):
        raise ValueError("receipt requires exactly one of focus or precommit")
    if precommit is None:
        schema = "spiral-oracle.selection-receipt/v1"
        commitment = {"focus": focus}
        domain = b"spiral-oracle-selection-receipt-v1\0"
    else:
        if selector_spec is None:
            raise ValueError("v2 receipt requires a selector spec")
        schema = "spiral-oracle.selection-receipt/v2"
        commitment = {"precommit": precommit, "selector_spec": selector_spec}
        domain = b"spiral-oracle-selection-receipt-v2\0"
    receipt = {
        "schema": schema,
        **commitment,
        "timestamp": timestamp,
        "mode": mode,
        "effective_weights": weights,
        "explicit_backend": explicit_backend,
        "rolls": rolls,
        "selected_backends": selected_backends,
    }
    return hashlib.sha256(domain + canonical_json(receipt)).hexdigest()


def decode_replay_token(token: str) -> dict[str, Any]:
    if not token or len(token) > MAX_REPLAY_TOKEN_LENGTH:
        raise ValueError("replay token is empty or too large")
    padding = "=" * (-len(token) % 4)
    try:
        decoded = base64.b64decode(token + padding, altchars=b"-_", validate=True)
        payload = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid replay token") from exc
    if not isinstance(payload, dict):
        raise ValueError("invalid replay token payload")
    return payload


def backend_metadata(backend_id: str) -> dict[str, Any]:
    module = BACKENDS[backend_id]
    minimum, maximum = allowed_weight_range(module.BASE_WEIGHT)
    return {
        "id": backend_id,
        "display_name": module.DISPLAY_NAME,
        "base_weight": module.BASE_WEIGHT,
        "allowed_weight_range": {"minimum": minimum, "maximum": maximum},
        "uses_timestamp": module.USES_TIMESTAMP,
        "required_inputs": list(module.REQUIRED_INPUTS),
        "result_schema": module.BACKEND_SCHEMA,
        "replay_schema": module.REPLAY_SCHEMA,
        "eligible": not module.REQUIRED_INPUTS,
    }


def output_precommit(replay_payload: dict[str, Any]) -> dict[str, Any]:
    if replay_payload["schema"] in PRECOMMIT_REPLAY_SCHEMAS:
        return copy.deepcopy(replay_payload["precommit"])
    return {
        "schema": None,
        "focus": replay_payload["focus"],
        "prior_frame": None,
        "tentative_next_step": None,
        "influence": {"level": None, "allowed_envelope": None},
        "legacy_unrecorded": True,
    }


def build_output(
    replay_payload: dict[str, Any],
    selection_steps: list[dict[str, Any]],
    public_runs: list[dict[str, Any]],
    *,
    execution_mode: str,
) -> dict[str, Any]:
    token, checksum = encode_replay_token(replay_payload)
    timestamp, timestamp_info = parse_timestamp(replay_payload["timestamp"])
    if timestamp != replay_payload["timestamp"]:
        raise ValueError("replay timestamp is not canonical")

    selection_payload = replay_payload["selection"]
    selector_spec = selection_payload.get("selector_spec", SELECTOR_SPEC_V1)
    base_weights = SELECTOR_SPECS[selector_spec]
    weights = selection_payload["effective_weights"]
    precommit = output_precommit(replay_payload)
    is_legacy = replay_payload["schema"] == LEGACY_REPLAY_SCHEMA
    stored_fields = (
        ["focus"]
        if is_legacy
        else [
            "focus",
            "prior_frame",
            "tentative_next_step",
            "influence.allowed_envelope",
        ]
    )
    return {
        "schema": SCHEMA_VERSION,
        "execution_mode": execution_mode,
        "replay_payload_schema": replay_payload["schema"],
        "focus": precommit["focus"],
        "precommit": precommit,
        "timestamp": timestamp_info,
        "selection": {
            "mode": selection_payload["mode"],
            "selector_spec": selector_spec,
            "ordering": "all backends selected before any backend output is generated",
            "base_weights": dict(base_weights),
            "effective_weights": weights,
            "model_adjustments": {
                backend_id: weights[backend_id] - base_weights[backend_id]
                for backend_id in weights
            },
            "adjustment_note": (
                "The ±25% bound applies to integer weights, not normalized probabilities."
            ),
            "steps": selection_steps,
            "selected_backends": [run["backend"] for run in public_runs],
            "selection_receipt_sha256": selection_payload["receipt_sha256"],
            "receipt_warning": (
                "Computed before backend generation by this program, but not externally "
                "timestamped, signed, or immutable."
            ),
            "dual_selection_note": (
                "With exactly two recorded backends, dual-distinct runs both and "
                "weights affect order only."
                if selection_payload["mode"] == "dual-distinct" and len(weights) == 2
                else (
                    "With three or more recorded backends, dual-distinct samples two "
                    "without replacement; weights affect membership and order."
                    if selection_payload["mode"] == "dual-distinct"
                    else None
                )
            ),
        },
        "readings": public_runs,
        "oracle_contract": copy.deepcopy(ORACLE_CONTRACT),
        "audit_boundary": (
            "The draw does not establish facts, grant permission, or widen the "
            "precommitted influence envelope."
        ),
        "context_policy": {
            "stored_caller_text_fields": stored_fields,
            "full_conversation_stored": False,
            "caller_must_remove_sensitive_data": True,
            "script_limit": (
                "The script validates shape but cannot reliably detect names, credentials, or private data."
            ),
        },
        "replay": {
            "token": token,
            "sha256": checksum,
            "checksum_scope": "canonical replay payload",
            "authenticity_warning": (
                "This checksum detects accidental change when recorded separately; it is not a signature."
            ),
            "privacy_warning": (
                "The token is base64-encoded, not encrypted, and contains the "
                + (
                    "caller-supplied normalized focus"
                    if is_legacy
                    else "recorded caller-supplied precommit text fields"
                )
                + (
                    "; an astrology run also records the thread-start timestamp, "
                    "OS timezone, and the timezone's public zone.tab reference "
                    "point, but not the raw thread identifier"
                    if "spiral-western-astrology"
                    in selection_payload["selected_backends"]
                    else ""
                )
                + "; the caller must remove sensitive data."
            ),
        },
    }


def run_live(
    *,
    focus: str,
    prior_frame: str,
    tentative_next_step: str,
    influence_level: str,
    allowed_envelope: str,
    mode: str,
    explicit_backend: str | None,
    overrides: Sequence[tuple[str, int]],
    timestamp_arg: str | None,
) -> dict[str, Any]:
    validate_registry()
    validate_live_request(mode, explicit_backend, overrides)
    precommit = normalize_precommit(
        focus=focus,
        prior_frame=prior_frame,
        tentative_next_step=tentative_next_step,
        influence_level=influence_level,
        allowed_envelope=allowed_envelope,
    )
    timestamp, _ = parse_timestamp(timestamp_arg)
    weights, _ = build_effective_weights(overrides)
    selected, steps, rolls = select_backends(
        mode,
        weights,
        explicit_backend=explicit_backend,
    )

    receipt_sha256 = selection_receipt_sha256(
        precommit=precommit,
        selector_spec=CURRENT_SELECTOR_SPEC,
        timestamp=timestamp,
        mode=mode,
        weights=weights,
        explicit_backend=explicit_backend,
        rolls=rolls,
        selected_backends=selected,
    )

    # Selection is fully fixed before the first backend generates any output.
    public_runs = []
    replay_runs = []
    for backend_id in selected:
        module = BACKENDS[backend_id]
        result, backend_replay = module.generate(timestamp)
        public_runs.append(
            {
                "backend": backend_id,
                "display_name": module.DISPLAY_NAME,
                "uses_timestamp": module.USES_TIMESTAMP,
                "result": result,
            }
        )
        replay_runs.append({"backend": backend_id, "payload": backend_replay})

    replay_payload = {
        "schema": REPLAY_SCHEMA,
        "precommit": precommit,
        "timestamp": timestamp,
        "selection": {
            "selector_spec": CURRENT_SELECTOR_SPEC,
            "mode": mode,
            "effective_weights": weights,
            "explicit_backend": explicit_backend,
            "rolls": rolls,
            "selected_backends": selected,
            "receipt_sha256": receipt_sha256,
        },
        "backend_runs": replay_runs,
    }
    return build_output(
        replay_payload, steps, public_runs, execution_mode="live-random"
    )


def validate_replay_shape(payload: dict[str, Any]) -> None:
    schema = payload.get("schema")
    if schema in PRECOMMIT_REPLAY_SCHEMAS:
        expected = {"schema", "precommit", "timestamp", "selection", "backend_runs"}
    elif schema == LEGACY_REPLAY_SCHEMA:
        expected = {"schema", "focus", "timestamp", "selection", "backend_runs"}
    else:
        raise ValueError("replay token has an unsupported schema or shape")
    if set(payload) != expected:
        raise ValueError("replay token has an unsupported schema or shape")
    if not isinstance(payload["selection"], dict):
        raise ValueError("invalid replay selection")
    selection_keys = {
        "mode",
        "effective_weights",
        "explicit_backend",
        "rolls",
        "selected_backends",
        "receipt_sha256",
    }
    if schema in PRECOMMIT_REPLAY_SCHEMAS:
        selection_keys.add("selector_spec")
    if set(payload["selection"]) != selection_keys:
        raise ValueError("invalid replay selection shape")
    if not isinstance(payload["backend_runs"], list):
        raise ValueError("invalid replay backend runs")


def run_replay(token: str) -> dict[str, Any]:
    validate_registry()
    payload = decode_replay_token(token)
    validate_replay_shape(payload)
    if payload["schema"] in PRECOMMIT_REPLAY_SCHEMAS:
        precommit = validate_precommit_payload(payload["precommit"])
        normalized_focus = precommit["focus"]
    else:
        precommit = None
        normalized_focus = normalize_focus(payload["focus"])
        if normalized_focus != payload["focus"]:
            raise ValueError("replay focus is not canonical")
    timestamp, _ = parse_timestamp(payload["timestamp"])
    if timestamp != payload["timestamp"]:
        raise ValueError("replay timestamp is not canonical")

    selection = payload["selection"]
    expected_selector_spec = REPLAY_SELECTOR_SPECS[payload["schema"]]
    selector_spec = (
        selection["selector_spec"]
        if payload["schema"] in PRECOMMIT_REPLAY_SCHEMAS
        else expected_selector_spec
    )
    if selector_spec != expected_selector_spec:
        raise ValueError("replay token has an unsupported selector spec")
    weights = validate_effective_weights(selection["effective_weights"], selector_spec)
    rolls = selection["rolls"]
    if not isinstance(rolls, list):
        raise ValueError("replay selector rolls must be a list")
    explicit_backend = selection["explicit_backend"]
    if explicit_backend is not None and not isinstance(explicit_backend, str):
        raise ValueError("invalid explicit backend in replay token")
    selected, steps, canonical_rolls = select_backends(
        selection["mode"],
        weights,
        explicit_backend=explicit_backend,
        supplied_rolls=rolls,
    )
    if canonical_rolls != rolls:
        raise ValueError("replay selector rolls are not canonical")
    if selection["selected_backends"] != selected:
        raise ValueError("replay selected backends do not match selector rolls")
    expected_receipt = selection_receipt_sha256(
        focus=normalized_focus if precommit is None else None,
        precommit=precommit,
        selector_spec=selector_spec if precommit is not None else None,
        timestamp=timestamp,
        mode=selection["mode"],
        weights=weights,
        explicit_backend=explicit_backend,
        rolls=rolls,
        selected_backends=selected,
    )
    if selection["receipt_sha256"] != expected_receipt:
        raise ValueError("replay selection receipt checksum does not match")

    backend_runs = payload["backend_runs"]
    if len(backend_runs) != len(selected):
        raise ValueError("replay backend count does not match selection")
    public_runs = []
    for expected_backend, run in zip(selected, backend_runs):
        if not isinstance(run, dict) or set(run) != {"backend", "payload"}:
            raise ValueError("invalid replay backend entry")
        if run["backend"] != expected_backend:
            raise ValueError("replay backend order does not match selector output")
        module = BACKENDS[expected_backend]
        result = module.replay(run["payload"], timestamp)
        public_runs.append(
            {
                "backend": expected_backend,
                "display_name": module.DISPLAY_NAME,
                "uses_timestamp": module.USES_TIMESTAMP,
                "result": result,
            }
        )

    payload["selection"]["effective_weights"] = weights
    return build_output(payload, steps, public_runs, execution_mode="replay")


def format_text(output: dict[str, Any]) -> str:
    if "backends" in output:
        lines = ["Spiral Oracle backends"]
        for backend in output["backends"]:
            eligibility = "eligible" if backend["eligible"] else "ineligible"
            allowed = backend["allowed_weight_range"]
            lines.append(
                f"- {backend['id']}: base {backend['base_weight']}, "
                f"allowed {allowed['minimum']}..{allowed['maximum']}, {eligibility}"
            )
        return "\n".join(lines)

    lines = [
        "Spiral Oracle",
        f"Focus: {json.dumps(output['focus'], ensure_ascii=False)}",
    ]
    precommit = output["precommit"]
    if precommit["prior_frame"] is not None:
        lines.extend(
            [
                f"Prior frame: {json.dumps(precommit['prior_frame'], ensure_ascii=False)}",
                "Tentative next step: "
                + json.dumps(precommit["tentative_next_step"], ensure_ascii=False),
                f"Permitted influence: {precommit['influence']['level']} — "
                f"{precommit['influence']['allowed_envelope']}",
            ]
        )
    else:
        lines.append("Precommit trace: unavailable in legacy v1 replay")
    lines.extend(
        [
            f"Timestamp: {output['timestamp']['captured_at']}",
            f"Mode: {output['selection']['mode']}",
            "Selected: " + ", ".join(output["selection"]["selected_backends"]),
        ]
    )

    for step_number, step in enumerate(output["selection"]["steps"], start=1):
        if step["roll_zero_based"] is not None:
            lines.append(
                f"Selector step {step_number}: roll {step['roll_zero_based']} of "
                f"0..{step['total_weight'] - 1} -> {step['selected_backend']}"
            )

    for reading in output["readings"]:
        result = reading["result"]
        lines.append(f"Backend: {reading['display_name']}")
        if reading["backend"] == "spiral-iching":
            primary = result["primary_hexagram"]
            lines.append(
                f"Primary: {primary['unicode']} #{primary['number']} {primary['han']} "
                f"{primary['pinyin']} — {primary['english_name']}"
            )
            lines.append(
                "Changing lines: "
                + (", ".join(map(str, result["moving_lines"])) or "none")
            )
            if result["relating_hexagram"] is not None:
                relating = result["relating_hexagram"]
                lines.append(
                    f"Relating: {relating['unicode']} #{relating['number']} "
                    f"{relating['han']} {relating['pinyin']} — {relating['english_name']}"
                )
            lines.append(f"Raw coins: {result['raw_cast_bottom_to_top']}")
        elif reading["backend"] == "symbolic-prompt":
            lines.append(f"Prompt: {result['prompt']}")
        elif reading["backend"] == "spiral-tarot":
            draw = result["draw"]
            lines.append(
                f"Card: {draw['card']['name']} ({draw['orientation']}); "
                f"catalog index {draw['card_index']}"
            )
        elif reading["backend"] == "spiral-western-astrology":
            solar = result["oracle_moment_sun"]
            timezone_context = solar["os_timezone_context"]
            timezone_label = (
                timezone_context["timezone_id"]
                if timezone_context["available"]
                else "IANA timezone unavailable"
            )
            lines.append(
                f"Oracle Sun: {solar['sign']['glyph']} {solar['sign']['name']} "
                f"{solar['degree_within_sign']}°; longitude "
                f"{solar['longitude_degrees']}°; OS timezone {timezone_label}"
            )
            thread_sun = result["thread_nativity_sun"]
            if thread_sun["available"]:
                origin = thread_sun["origin"]
                reference = origin["reference_point"]
                lines.append(
                    f"Thread Sun: {thread_sun['sign']['glyph']} "
                    f"{thread_sun['sign']['name']} "
                    f"{thread_sun['degree_within_sign']}°; thread start "
                    f"{origin['thread_start_local']} {origin['timezone_id']}; "
                    f"synthetic zone.tab point {reference['coordinate_text']}"
                )
            else:
                lines.append("Thread Sun: unavailable; " + thread_sun["reason"])
        elif reading["backend"] == "spiral-four-pillars":
            pillars = result["pillars"]
            lines.append(
                "Four Pillars: "
                + " / ".join(
                    f"{name} {pillars[name]['han']} {pillars[name]['latin']}"
                    for name in ("year", "month", "day", "hour")
                )
            )

    lines.extend(
        [
            f"Audit boundary: {output['audit_boundary']}",
            "Recorded-text privacy: caller-sanitized; this script validates shape but "
            "cannot detect names, credentials, or private data.",
            f"Replay-token privacy: {output['replay']['privacy_warning']}",
            f"Replay SHA-256: {output['replay']['sha256']}",
            f"Replay token: {output['replay']['token']}",
        ]
    )
    return "\n".join(lines)


def list_backends() -> dict[str, Any]:
    validate_registry()
    return {
        "schema": SCHEMA_VERSION,
        "backends": [backend_metadata(backend_id) for backend_id in BACKENDS],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select and draw one auditable Spiral Oracle backend."
    )
    parser.add_argument("--focus", help="short caller-sanitized reflection focus")
    parser.add_argument(
        "--prior-frame", help="caller-sanitized pre-draw view of the situation"
    )
    parser.add_argument(
        "--tentative-next-step", help="caller-sanitized pre-draw tentative next step"
    )
    parser.add_argument("--influence-level", choices=INFLUENCE_LEVELS)
    parser.add_argument(
        "--allowed-envelope",
        help="caller-sanitized boundary within which the draw may change the path",
    )
    parser.add_argument("--mode", choices=MODES)
    parser.add_argument("--backend", help="backend id required by single mode")
    parser.add_argument(
        "--weight",
        action="append",
        default=[],
        type=parse_weight_override,
        metavar="BACKEND=INTEGER",
        help="bounded pre-draw backend weight override; may be repeated",
    )
    parser.add_argument(
        "--timestamp",
        help="timezone-aware ISO 8601 timestamp for tests; live use captures now",
    )
    parser.add_argument(
        "--replay-token", help="reconstruct a prior draw without randomness"
    )
    parser.add_argument("--list-backends", action="store_true")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    validate_registry()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list_backends:
            if (
                any(
                    value is not None
                    for value in (
                        args.focus,
                        args.prior_frame,
                        args.tentative_next_step,
                        args.influence_level,
                        args.allowed_envelope,
                        args.mode,
                        args.backend,
                        args.timestamp,
                        args.replay_token,
                    )
                )
                or args.weight
            ):
                parser.error("--list-backends cannot be combined with draw options")
            output = list_backends()
        elif args.replay_token:
            if (
                any(
                    value is not None
                    for value in (
                        args.focus,
                        args.prior_frame,
                        args.tentative_next_step,
                        args.influence_level,
                        args.allowed_envelope,
                        args.mode,
                        args.backend,
                        args.timestamp,
                    )
                )
                or args.weight
            ):
                parser.error("--replay-token cannot be combined with live draw options")
            output = run_replay(args.replay_token)
        else:
            if args.focus is None:
                parser.error("a live draw requires --focus")
            required_precommit = {
                "--prior-frame": args.prior_frame,
                "--tentative-next-step": args.tentative_next_step,
                "--influence-level": args.influence_level,
                "--allowed-envelope": args.allowed_envelope,
            }
            missing = [
                name for name, value in required_precommit.items() if value is None
            ]
            if missing:
                parser.error("a live draw also requires " + ", ".join(missing))
            mode = args.mode or "auto-weighted"
            if mode == "single" and args.backend is None:
                parser.error("single mode requires --backend")
            if mode != "single" and args.backend is not None:
                parser.error("--backend is only valid in single mode")
            if mode == "single" and args.weight:
                parser.error("weight overrides are not meaningful in single mode")
            output = run_live(
                focus=args.focus,
                prior_frame=args.prior_frame,
                tentative_next_step=args.tentative_next_step,
                influence_level=args.influence_level,
                allowed_envelope=args.allowed_envelope,
                mode=mode,
                explicit_backend=args.backend,
                overrides=args.weight,
                timestamp_arg=args.timestamp,
            )
    except ValueError as exc:
        parser.error(str(exc))

    if args.format == "json":
        json.dump(output, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(format_text(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
