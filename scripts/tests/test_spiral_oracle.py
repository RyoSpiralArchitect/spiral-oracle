from __future__ import annotations

import base64
import hashlib
import itertools
import json
import os
import subprocess
import sys
import unittest
import unicodedata
from pathlib import Path
from unittest.mock import call, patch


SKILL = Path(__file__).resolve().parents[2]
SCRIPTS = SKILL / "scripts"
SCRIPT = SCRIPTS / "spiral_oracle.py"
sys.path.insert(0, str(SCRIPTS))

import spiral_oracle as oracle  # noqa: E402
from backends import (  # noqa: E402
    _solar,
    _thread_origin,
    four_pillars,
    iching,
    symbolic_prompt,
    tarot,
    western_astrology,
)


FIXED_TIME = "2026-08-29T15:04:05.123-07:00"
FIXED_THREAD_ID = "01972b7c-ec95-7abc-8def-0123456789ab"
ALL_OLD_YANG = ["HHH"] * 6
LEGACY_V1_TOKEN = (
    "eyJiYWNrZW5kX3J1bnMiOlt7ImJhY2tlbmQiOiJzeW1ib2xpYy1wcm9tcHQiLCJwYXlsb2FkIjp7"
    "ImNhdGFsb2dfdmVyc2lvbiI6InN5bWJvbGljLXRyaWFkLWVuL3YxIiwibGVuc19pbmRleCI6MiwibW"
    "90aW9uX2luZGV4IjoxLCJzY2hlbWEiOiJzcGlyYWwtb3JhY2xlLnJlcGxheS5zeW1ib2xpYy1wcm9t"
    "cHQvdjEiLCJzeW1ib2xfaW5kZXgiOjB9fV0sImZvY3VzIjoiTGVnYWN5IHJlcGxheSBmaXh0dXJlIiwi"
    "c2NoZW1hIjoic3BpcmFsLW9yYWNsZS5yZXBsYXkvdjEiLCJzZWxlY3Rpb24iOnsiZWZmZWN0aXZlX3dl"
    "aWdodHMiOnsic3BpcmFsLWljaGluZyI6MzAsInN5bWJvbGljLXByb21wdCI6MTB9LCJleHBsaWNpdF9i"
    "YWNrZW5kIjoic3ltYm9saWMtcHJvbXB0IiwibW9kZSI6InNpbmdsZSIsInJlY2VpcHRfc2hhMjU2Ijoi"
    "OGZkM2ZmZDc3MjAxMjc2MjY2ZDY0OTM4Y2M3NzZmOTVjNGMxZTMxZDhjMDZjZjZlNzVlMDkyMDliZDhi"
    "MmU2MiIsInJvbGxzIjpbXSwic2VsZWN0ZWRfYmFja2VuZHMiOlsic3ltYm9saWMtcHJvbXB0Il19LCJ0"
    "aW1lc3RhbXAiOiIyMDI2LTA4LTI5VDE1OjA0OjA1LjEyMy0wNzowMCJ9"
)
LEGACY_V1_SHA256 = "d0981dbf406884fd7d373b776a4c88432656e23d67e10a3d62d7a7ae056aad34"
LEGACY_V1_AUTO_TOKEN = (
    "eyJiYWNrZW5kX3J1bnMiOlt7ImJhY2tlbmQiOiJzeW1ib2xpYy1wcm9tcHQiLCJwYXlsb2Fk"
    "Ijp7ImNhdGFsb2dfdmVyc2lvbiI6InN5bWJvbGljLXRyaWFkLWVuL3YxIiwibGVuc19pbmRle"
    "CI6MCwibW90aW9uX2luZGV4IjowLCJzY2hlbWEiOiJzcGlyYWwtb3JhY2xlLnJlcGxheS5zeW"
    "1ib2xpYy1wcm9tcHQvdjEiLCJzeW1ib2xfaW5kZXgiOjB9fV0sImZvY3VzIjoiTGVnYWN5IHdl"
    "aWdodGVkL2R1YWwgY2hlY2siLCJzY2hlbWEiOiJzcGlyYWwtb3JhY2xlLnJlcGxheS92MSIsIn"
    "NlbGVjdGlvbiI6eyJlZmZlY3RpdmVfd2VpZ2h0cyI6eyJzcGlyYWwtaWNoaW5nIjozMCwic3lt"
    "Ym9saWMtcHJvbXB0IjoxMH0sImV4cGxpY2l0X2JhY2tlbmQiOm51bGwsIm1vZGUiOiJhdXRvLX"
    "dlaWdodGVkIiwicmVjZWlwdF9zaGEyNTYiOiIxOWFhMzIwZjM0Njg2ODg3NzJjY2ZlYzI2MDc0"
    "NzgwZjc4ZDQxZWJmMWY3MGJjYjU1MTk0ZTQ0Y2VlNGYwNjFkIiwicm9sbHMiOlszNV0sInNlbG"
    "VjdGVkX2JhY2tlbmRzIjpbInN5bWJvbGljLXByb21wdCJdfSwidGltZXN0YW1wIjoiMjAyNi0w"
    "OC0yOVQxNTowNDowNS4xMjMtMDc6MDAifQ"
)
LEGACY_V1_AUTO_SHA256 = (
    "ca8be25c3f77e0cdac0b074cb3d8024763f327e93619be5ea311571135496aba"
)
LEGACY_V1_AUTO_READINGS_SHA256 = (
    "6d4274be6f0d899e5568b74347ac299da23cf88a8e03a8297dcdeeb4ade65be7"
)
LEGACY_V1_DUAL_TOKEN = (
    "eyJiYWNrZW5kX3J1bnMiOlt7ImJhY2tlbmQiOiJzeW1ib2xpYy1wcm9tcHQiLCJwYXlsb2Fk"
    "Ijp7ImNhdGFsb2dfdmVyc2lvbiI6InN5bWJvbGljLXRyaWFkLWVuL3YxIiwibGVuc19pbmRle"
    "CI6MCwibW90aW9uX2luZGV4IjowLCJzY2hlbWEiOiJzcGlyYWwtb3JhY2xlLnJlcGxheS5zeW"
    "1ib2xpYy1wcm9tcHQvdjEiLCJzeW1ib2xfaW5kZXgiOjB9fSx7ImJhY2tlbmQiOiJzcGlyYWwt"
    "aWNoaW5nIiwicGF5bG9hZCI6eyJjb2luc19ib3R0b21fdG9fdG9wIjpbIkhISCIsIkhISCIsIk"
    "hISCIsIkhISCIsIkhISCIsIkhISCJdLCJydWxlc2V0X3ZlcnNpb24iOiJ0aHJlZS1jb2luLWtp"
    "bmctd2VuL3YxIiwic2NoZW1hIjoic3BpcmFsLW9yYWNsZS5yZXBsYXkuaWNoaW5nL3YxIn19XS"
    "wiZm9jdXMiOiJMZWdhY3kgd2VpZ2h0ZWQvZHVhbCBjaGVjayIsInNjaGVtYSI6InNwaXJhbC1v"
    "cmFjbGUucmVwbGF5L3YxIiwic2VsZWN0aW9uIjp7ImVmZmVjdGl2ZV93ZWlnaHRzIjp7InNwaX"
    "JhbC1pY2hpbmciOjMwLCJzeW1ib2xpYy1wcm9tcHQiOjEwfSwiZXhwbGljaXRfYmFja2VuZCI6"
    "bnVsbCwibW9kZSI6ImR1YWwtZGlzdGluY3QiLCJyZWNlaXB0X3NoYTI1NiI6IjVlYTFhODE3OT"
    "M4YzVjMjk3OTk4NDRlMDk0YWI5ODNlODkxNTllYjI4OTg1NWU4Y2VkYWQwOTcwMjVlN2EwNDki"
    "LCJyb2xscyI6WzM1LDBdLCJzZWxlY3RlZF9iYWNrZW5kcyI6WyJzeW1ib2xpYy1wcm9tcHQiLC"
    "JzcGlyYWwtaWNoaW5nIl19LCJ0aW1lc3RhbXAiOiIyMDI2LTA4LTI5VDE1OjA0OjA1LjEyMy0w"
    "NzowMCJ9"
)
LEGACY_V1_DUAL_SHA256 = (
    "f56fde4ac351f1158ebfef187933fd9615adce8394324518de346d08b7dfdd36"
)
LEGACY_V1_DUAL_READINGS_SHA256 = (
    "1758839a2b7390fc4d6dcfea60d08820bde4a1daa59ae22efaa9555914314549"
)
LEGACY_V2_AUTO_TOKEN = (
    "eyJiYWNrZW5kX3J1bnMiOlt7ImJhY2tlbmQiOiJzcGlyYWwtdGFyb3QiLCJwYXlsb2FkIjp7"
    "ImNhcmRfaW5kZXgiOjc3LCJjYXRhbG9nX3ZlcnNpb24iOiJ3YWl0ZS1zbWl0aC1pZGVudGlm"
    "aWVycy1lbi92MSIsIm9yaWVudGF0aW9uX2JpdCI6MSwicnVsZXNldF92ZXJzaW9uIjoic2lu"
    "Z2xlLWNhcmQtaW5kZXBlbmRlbnQtb3JpZW50YXRpb24vdjEiLCJzY2hlbWEiOiJzcGlyYWwt"
    "b3JhY2xlLnJlcGxheS50YXJvdC92MSJ9fV0sInByZWNvbW1pdCI6eyJmb2N1cyI6IkZyb3pl"
    "biB2MiBjb21wYXRpYmlsaXR5IGZpeHR1cmUiLCJpbmZsdWVuY2UiOnsiYWxsb3dlZF9lbnZl"
    "bG9wZSI6Ik1heSByZW9yZGVyIG9ubHkgbG9jYWwgcmV2ZXJzaWJsZSBjaGVja3MiLCJsZXZl"
    "bCI6InByb2JlIn0sInByaW9yX2ZyYW1lIjoiQ3VycmVudCB2MiBmcmFtZSIsInNjaGVtYSI6"
    "InNwaXJhbC1vcmFjbGUucHJlY29tbWl0L3YxIiwidGVudGF0aXZlX25leHRfc3RlcCI6Iktl"
    "ZXAgdGhlIGN1cnJlbnQgbG9jYWwgb3JkZXIifSwic2NoZW1hIjoic3BpcmFsLW9yYWNsZS5y"
    "ZXBsYXkvdjIiLCJzZWxlY3Rpb24iOnsiZWZmZWN0aXZlX3dlaWdodHMiOnsic3BpcmFsLWlj"
    "aGluZyI6MzAsInNwaXJhbC10YXJvdCI6MjUsInN5bWJvbGljLXByb21wdCI6MTB9LCJleHBs"
    "aWNpdF9iYWNrZW5kIjpudWxsLCJtb2RlIjoiYXV0by13ZWlnaHRlZCIsInJlY2VpcHRfc2hh"
    "MjU2IjoiMzY4ZTdlMzlmYTMzNGNlYjBkYzQ5ZWI4ZjkxZmI3ZGZjZmZmYWM0NzY5YjgzMzI5"
    "YzU1OWUyZGVmYWUzNmU5ZSIsInJvbGxzIjpbMzVdLCJzZWxlY3RlZF9iYWNrZW5kcyI6WyJz"
    "cGlyYWwtdGFyb3QiXSwic2VsZWN0b3Jfc3BlYyI6InNwaXJhbC1vcmFjbGUuc2VsZWN0b3Iv"
    "djIifSwidGltZXN0YW1wIjoiMjAyNi0wOC0yOVQxNTowNDowNS4xMjMtMDc6MDAifQ"
)
LEGACY_V2_AUTO_SHA256 = (
    "f160fa4774d0ba2bf36d824960307c6aa88f99587487076646f3b4925ee0d328"
)
LEGACY_V2_AUTO_READINGS_SHA256 = (
    "0dcc9636733a211dc7029ddbc6ec1760f1bdabf5bb4a4e8e854a68eb4ac130d3"
)
LEGACY_V2_DUAL_TOKEN = (
    "eyJiYWNrZW5kX3J1bnMiOlt7ImJhY2tlbmQiOiJzeW1ib2xpYy1wcm9tcHQiLCJwYXlsb2Fk"
    "Ijp7ImNhdGFsb2dfdmVyc2lvbiI6InN5bWJvbGljLXRyaWFkLWVuL3YxIiwibGVuc19pbmRl"
    "eCI6MiwibW90aW9uX2luZGV4IjoxLCJzY2hlbWEiOiJzcGlyYWwtb3JhY2xlLnJlcGxheS5z"
    "eW1ib2xpYy1wcm9tcHQvdjEiLCJzeW1ib2xfaW5kZXgiOjB9fSx7ImJhY2tlbmQiOiJzcGly"
    "YWwtdGFyb3QiLCJwYXlsb2FkIjp7ImNhcmRfaW5kZXgiOjc3LCJjYXRhbG9nX3ZlcnNpb24i"
    "OiJ3YWl0ZS1zbWl0aC1pZGVudGlmaWVycy1lbi92MSIsIm9yaWVudGF0aW9uX2JpdCI6MSwi"
    "cnVsZXNldF92ZXJzaW9uIjoic2luZ2xlLWNhcmQtaW5kZXBlbmRlbnQtb3JpZW50YXRpb24v"
    "djEiLCJzY2hlbWEiOiJzcGlyYWwtb3JhY2xlLnJlcGxheS50YXJvdC92MSJ9fV0sInByZWNv"
    "bW1pdCI6eyJmb2N1cyI6IkZyb3plbiB2MiBjb21wYXRpYmlsaXR5IGZpeHR1cmUiLCJpbmZs"
    "dWVuY2UiOnsiYWxsb3dlZF9lbnZlbG9wZSI6Ik1heSByZW9yZGVyIG9ubHkgbG9jYWwgcmV2"
    "ZXJzaWJsZSBjaGVja3MiLCJsZXZlbCI6InByb2JlIn0sInByaW9yX2ZyYW1lIjoiQ3VycmVu"
    "dCB2MiBmcmFtZSIsInNjaGVtYSI6InNwaXJhbC1vcmFjbGUucHJlY29tbWl0L3YxIiwidGVu"
    "dGF0aXZlX25leHRfc3RlcCI6IktlZXAgdGhlIGN1cnJlbnQgbG9jYWwgb3JkZXIifSwic2No"
    "ZW1hIjoic3BpcmFsLW9yYWNsZS5yZXBsYXkvdjIiLCJzZWxlY3Rpb24iOnsiZWZmZWN0aXZl"
    "X3dlaWdodHMiOnsic3BpcmFsLWljaGluZyI6MzAsInNwaXJhbC10YXJvdCI6MjUsInN5bWJv"
    "bGljLXByb21wdCI6MTB9LCJleHBsaWNpdF9iYWNrZW5kIjpudWxsLCJtb2RlIjoiZHVhbC1k"
    "aXN0aW5jdCIsInJlY2VpcHRfc2hhMjU2IjoiMmIzY2VjMmQ1MDg0MzYyYWUxZDhjMTk2OGY1"
    "ODg5YTZlNTZkMTVlYzk2YmU5MTYzNWU4MjFhZTQ4MDJlMTc2MyIsInJvbGxzIjpbNjAsMzBd"
    "LCJzZWxlY3RlZF9iYWNrZW5kcyI6WyJzeW1ib2xpYy1wcm9tcHQiLCJzcGlyYWwtdGFyb3Qi"
    "XSwic2VsZWN0b3Jfc3BlYyI6InNwaXJhbC1vcmFjbGUuc2VsZWN0b3IvdjIifSwidGltZXN0"
    "YW1wIjoiMjAyNi0wOC0yOVQxNTowNDowNS4xMjMtMDc6MDAifQ"
)
LEGACY_V2_DUAL_SHA256 = (
    "f22b2a0ec5c23797c28fe732da7a5df5ab5e340d0208f5eb6982123aea130937"
)
LEGACY_V2_DUAL_READINGS_SHA256 = (
    "60b47a53d9da3ca42a446463b3bf1b6fc9edc5e67afa1f0df0c3ce61324a3b47"
)


def run_live(
    *,
    focus: str,
    mode: str,
    explicit_backend: str | None,
    overrides,
    timestamp_arg: str | None,
):
    return oracle.run_live(
        focus=focus,
        prior_frame="Current frame before the draw",
        tentative_next_step="Run the already planned local check",
        influence_level="probe",
        allowed_envelope="May alter only local reversible checks",
        mode=mode,
        explicit_backend=explicit_backend,
        overrides=overrides,
        timestamp_arg=timestamp_arg,
    )


def nested_keys(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from nested_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from nested_keys(nested)


class SelectorTests(unittest.TestCase):
    def test_registry_and_allowed_ranges(self) -> None:
        oracle.validate_registry()
        self.assertEqual(
            oracle.eligible_backend_ids(),
            [
                "spiral-iching",
                "spiral-tarot",
                "spiral-western-astrology",
                "spiral-four-pillars",
                "symbolic-prompt",
            ],
        )
        self.assertEqual(oracle.allowed_weight_range(30), (23, 37))
        self.assertEqual(oracle.allowed_weight_range(25), (19, 31))
        self.assertEqual(oracle.allowed_weight_range(20), (15, 25))
        self.assertEqual(oracle.allowed_weight_range(15), (12, 18))
        self.assertEqual(oracle.allowed_weight_range(10), (8, 12))

    def test_weight_overrides_are_bounded_and_unique(self) -> None:
        weights, _ = oracle.build_effective_weights(
            [
                ("spiral-iching", 37),
                ("spiral-tarot", 31),
                ("spiral-western-astrology", 25),
                ("spiral-four-pillars", 18),
                ("symbolic-prompt", 8),
            ]
        )
        self.assertEqual(
            weights,
            {
                "spiral-iching": 37,
                "spiral-tarot": 31,
                "spiral-western-astrology": 25,
                "spiral-four-pillars": 18,
                "symbolic-prompt": 8,
            },
        )
        with self.assertRaisesRegex(ValueError, "between 23 and 37"):
            oracle.build_effective_weights([("spiral-iching", 38)])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            oracle.build_effective_weights(
                [("spiral-iching", 30), ("spiral-iching", 31)]
            )

    def test_weighted_half_open_boundaries(self) -> None:
        weights = {
            "spiral-iching": 30,
            "spiral-tarot": 25,
            "spiral-western-astrology": 20,
            "spiral-four-pillars": 15,
            "symbolic-prompt": 10,
        }
        for roll in (0, 29):
            selected, _ = oracle.weighted_pick(list(weights), weights, roll)
            self.assertEqual(selected, "spiral-iching")
        for roll in (30, 54):
            selected, _ = oracle.weighted_pick(list(weights), weights, roll)
            self.assertEqual(selected, "spiral-tarot")
        for roll in (55, 74):
            selected, _ = oracle.weighted_pick(list(weights), weights, roll)
            self.assertEqual(selected, "spiral-western-astrology")
        for roll in (75, 89):
            selected, _ = oracle.weighted_pick(list(weights), weights, roll)
            self.assertEqual(selected, "spiral-four-pillars")
        for roll in (90, 99):
            selected, _ = oracle.weighted_pick(list(weights), weights, roll)
            self.assertEqual(selected, "symbolic-prompt")
        with self.assertRaisesRegex(ValueError, "outside"):
            oracle.weighted_pick(list(weights), weights, 100)

    def test_dual_is_distinct_and_weights_affect_membership_and_order(self) -> None:
        weights = {
            "spiral-iching": 30,
            "spiral-tarot": 25,
            "spiral-western-astrology": 20,
            "spiral-four-pillars": 15,
            "symbolic-prompt": 10,
        }
        selected, steps, rolls = oracle.select_backends(
            "dual-distinct", weights, supplied_rolls=[95, 60]
        )
        self.assertEqual(selected, ["symbolic-prompt", "spiral-western-astrology"])
        self.assertEqual(len(set(selected)), 2)
        self.assertEqual(rolls, [95, 60])
        self.assertEqual(steps[1]["total_weight"], 90)

    def test_focus_is_nfc_single_line_and_rejects_bidi_control(self) -> None:
        decomposed = "Cafe\u0301\nnext"
        normalized = oracle.normalize_focus(decomposed)
        self.assertEqual(normalized, unicodedata.normalize("NFC", "Café next"))
        with self.assertRaisesRegex(ValueError, "control, format"):
            oracle.normalize_focus("safe\u202eevil")
        with self.assertRaisesRegex(ValueError, "influence level"):
            oracle.normalize_precommit(
                focus="Question",
                prior_frame="Prior",
                tentative_next_step="Next",
                influence_level="deploy",
                allowed_envelope="Anything",
            )

    def test_timestamp_requires_offset_and_is_canonical(self) -> None:
        with self.assertRaisesRegex(ValueError, "ISO 8601 text"):
            oracle.parse_timestamp(42)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            oracle.parse_timestamp("2026-08-29T15:04:05")
        canonical, info = oracle.parse_timestamp("2026-08-29T22:04:05.123Z")
        self.assertEqual(canonical, "2026-08-29T22:04:05.123+00:00")
        self.assertEqual(info["captured_at_utc"], canonical)
        self.assertEqual(info["utc_offset"], "+00:00")
        self.assertNotIn("timezone_name", info)

    def test_imported_live_api_matches_cli_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "BACKEND, INTEGER"):
            run_live(
                focus="API check",
                mode="auto-weighted",
                explicit_backend=None,
                overrides=[("spiral-iching", 30.0)],  # type: ignore[list-item]
                timestamp_arg=FIXED_TIME,
            )
        with self.assertRaisesRegex(ValueError, "not meaningful"):
            run_live(
                focus="API check",
                mode="single",
                explicit_backend="spiral-iching",
                overrides=[("spiral-iching", 30)],
                timestamp_arg=FIXED_TIME,
            )
        with self.assertRaisesRegex(ValueError, "only valid"):
            run_live(
                focus="API check",
                mode="auto-weighted",
                explicit_backend="spiral-iching",
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )

    def test_imported_entry_points_validate_registry(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[0, 1, 2]):
            live = run_live(
                focus="Registry parity fixture",
                mode="single",
                explicit_backend="symbolic-prompt",
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )

        with patch.object(tarot, "BACKEND_ID", "registry-mismatch"):
            calls = (
                lambda: run_live(
                    focus="Registry parity live",
                    mode="single",
                    explicit_backend="symbolic-prompt",
                    overrides=[],
                    timestamp_arg=FIXED_TIME,
                ),
                lambda: oracle.run_replay(live["replay"]["token"]),
                oracle.list_backends,
            )
            for entry_point in calls:
                with self.subTest(entry_point=entry_point):
                    with self.assertRaisesRegex(RuntimeError, "registry key mismatch"):
                        entry_point()

    def test_contract_is_not_shared_between_results(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[95, 1, 2, 3]):
            first = run_live(
                focus="Contract isolation one",
                mode="auto-weighted",
                explicit_backend=None,
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        first["oracle_contract"]["grants_authority_or_permission"] = True
        with patch.object(oracle.secrets, "randbelow", side_effect=[95, 1, 2, 3]):
            second = run_live(
                focus="Contract isolation two",
                mode="auto-weighted",
                explicit_backend=None,
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        self.assertFalse(second["oracle_contract"]["grants_authority_or_permission"])

    def test_auto_live_replay_round_trip_symbolic_backend(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[95, 1, 2, 3]):
            live = run_live(
                focus="What deserves attention?",
                mode="auto-weighted",
                explicit_backend=None,
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        self.assertEqual(live["selection"]["selected_backends"], ["symbolic-prompt"])
        self.assertTrue(live["context_policy"]["caller_must_remove_sensitive_data"])
        self.assertIn("precommit text", live["replay"]["privacy_warning"])
        text = oracle.format_text(live)
        self.assertIn("Recorded-text privacy", text)
        self.assertIn("base64-encoded", text)
        self.assertIn("not encrypted", text)
        self.assertIn("precommit text", text)
        replayed = oracle.run_replay(live["replay"]["token"])
        self.assertEqual(replayed["execution_mode"], "replay")
        self.assertEqual(replayed["readings"], live["readings"])
        self.assertEqual(replayed["selection"], live["selection"])
        self.assertEqual(replayed["replay"]["sha256"], live["replay"]["sha256"])

    def test_auto_live_replay_round_trip_tarot_backend(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[35, 77, 1]):
            live = run_live(
                focus="What changes if the neglected edge is centered?",
                mode="auto-weighted",
                explicit_backend=None,
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        self.assertEqual(live["selection"]["selected_backends"], ["spiral-tarot"])
        self.assertEqual(
            live["readings"][0]["result"]["draw"]["card"]["name"],
            "King of Pentacles",
        )
        replayed = oracle.run_replay(live["replay"]["token"])
        self.assertEqual(replayed["readings"], live["readings"])
        self.assertEqual(replayed["replay"]["token"], live["replay"]["token"])

    def test_time_backends_round_trip_through_current_replay(self) -> None:
        expected_fragments = {
            "spiral-western-astrology": "Oracle Sun:",
            "spiral-four-pillars": "Four Pillars:",
        }
        for backend_id, text_fragment in expected_fragments.items():
            with self.subTest(backend=backend_id):
                live = run_live(
                    focus="What does this moment place at the edge of attention?",
                    mode="single",
                    explicit_backend=backend_id,
                    overrides=[],
                    timestamp_arg=FIXED_TIME,
                )
                self.assertEqual(live["replay_payload_schema"], oracle.REPLAY_SCHEMA)
                self.assertEqual(
                    live["selection"]["selector_spec"], oracle.SELECTOR_SPEC_V3
                )
                self.assertTrue(live["readings"][0]["uses_timestamp"])
                replayed = oracle.run_replay(live["replay"]["token"])
                self.assertEqual(replayed["readings"], live["readings"])
                self.assertEqual(replayed["replay"]["token"], live["replay"]["token"])
                self.assertIn(text_fragment, oracle.format_text(live))

    def test_dual_backends_receive_the_same_timestamp(self) -> None:
        seen: list[tuple[str, str]] = []

        def fake_iching(timestamp: str):
            seen.append(("spiral-iching", timestamp))
            return iching.cast(ALL_OLD_YANG), {
                "schema": iching.REPLAY_SCHEMA,
                "ruleset_version": iching.RULESET_VERSION,
                "coins_bottom_to_top": ALL_OLD_YANG,
            }

        def fake_symbolic(timestamp: str):
            seen.append(("symbolic-prompt", timestamp))
            payload = {
                "schema": symbolic_prompt.REPLAY_SCHEMA,
                "catalog_version": symbolic_prompt.CATALOG_VERSION,
                "symbol_index": 0,
                "motion_index": 0,
                "lens_index": 0,
            }
            return symbolic_prompt.replay(payload, timestamp), payload

        with (
            patch.object(oracle.secrets, "randbelow", side_effect=[95, 0]),
            patch.object(iching, "generate", side_effect=fake_iching),
            patch.object(symbolic_prompt, "generate", side_effect=fake_symbolic),
        ):
            output = run_live(
                focus="Shared timestamp check",
                mode="dual-distinct",
                explicit_backend=None,
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        self.assertEqual(
            seen,
            [("symbolic-prompt", FIXED_TIME), ("spiral-iching", FIXED_TIME)],
        )
        self.assertIn("samples two", output["selection"]["dual_selection_note"])

    def test_replay_rejects_selection_tampering(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[95, 1, 2, 3]):
            output = run_live(
                focus="Tamper check",
                mode="auto-weighted",
                explicit_backend=None,
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        payload = oracle.decode_replay_token(output["replay"]["token"])
        payload["selection"]["selected_backends"] = ["spiral-iching"]
        tampered_token, _ = oracle.encode_replay_token(payload)
        with self.assertRaisesRegex(ValueError, "do not match"):
            oracle.run_replay(tampered_token)

    def test_replay_selection_ignores_json_member_order(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[95, 1, 2, 3]):
            live = run_live(
                focus="JSON member order check",
                mode="auto-weighted",
                explicit_backend=None,
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        payload = oracle.decode_replay_token(live["replay"]["token"])
        original = payload["selection"]["effective_weights"]
        payload["selection"]["effective_weights"] = {
            "symbolic-prompt": original["symbolic-prompt"],
            "spiral-four-pillars": original["spiral-four-pillars"],
            "spiral-western-astrology": original["spiral-western-astrology"],
            "spiral-tarot": original["spiral-tarot"],
            "spiral-iching": original["spiral-iching"],
        }
        raw = json.dumps(
            payload, ensure_ascii=False, sort_keys=False, separators=(",", ":")
        ).encode("utf-8")
        reordered_token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

        replayed = oracle.run_replay(reordered_token)
        self.assertEqual(
            replayed["selection"]["selected_backends"], ["symbolic-prompt"]
        )
        canonical_replay = oracle.run_replay(replayed["replay"]["token"])
        self.assertEqual(
            canonical_replay["replay"]["token"], replayed["replay"]["token"]
        )

    def test_direct_cli_json_is_clean(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[0, 1, 2]):
            live = run_live(
                focus="CLI replay check",
                mode="single",
                explicit_backend="symbolic-prompt",
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        completed = subprocess.run(
            [
                str(SCRIPT),
                "--replay-token",
                live["replay"]["token"],
                "--format",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        parsed = json.loads(completed.stdout)
        self.assertEqual(parsed["selection"]["selected_backends"], ["symbolic-prompt"])
        self.assertEqual(parsed["execution_mode"], "replay")
        self.assertEqual(completed.stderr, "")

    def test_frozen_v1_token_replays_byte_identically(self) -> None:
        replayed = oracle.run_replay(LEGACY_V1_TOKEN)
        self.assertEqual(replayed["replay_payload_schema"], oracle.LEGACY_REPLAY_SCHEMA)
        self.assertEqual(replayed["replay"]["token"], LEGACY_V1_TOKEN)
        self.assertEqual(replayed["replay"]["sha256"], LEGACY_V1_SHA256)
        self.assertTrue(replayed["precommit"]["legacy_unrecorded"])
        self.assertEqual(
            replayed["selection"]["selector_spec"], oracle.SELECTOR_SPEC_V1
        )

    def test_frozen_v1_weighted_paths_replay_byte_identically(self) -> None:
        fixtures = (
            (
                LEGACY_V1_AUTO_TOKEN,
                LEGACY_V1_AUTO_SHA256,
                LEGACY_V1_AUTO_READINGS_SHA256,
                ["symbolic-prompt"],
                [35],
            ),
            (
                LEGACY_V1_DUAL_TOKEN,
                LEGACY_V1_DUAL_SHA256,
                LEGACY_V1_DUAL_READINGS_SHA256,
                ["symbolic-prompt", "spiral-iching"],
                [35, 0],
            ),
        )
        for token, checksum, readings_checksum, selected, rolls in fixtures:
            with self.subTest(selected=selected):
                replayed = oracle.run_replay(token)
                self.assertEqual(replayed["replay"]["token"], token)
                self.assertEqual(replayed["replay"]["sha256"], checksum)
                self.assertEqual(replayed["selection"]["selected_backends"], selected)
                self.assertEqual(
                    [
                        step["roll_zero_based"]
                        for step in replayed["selection"]["steps"]
                    ],
                    rolls,
                )
                self.assertEqual(
                    hashlib.sha256(
                        oracle.canonical_json(replayed["readings"])
                    ).hexdigest(),
                    readings_checksum,
                )

    def test_frozen_v2_weighted_paths_replay_byte_identically(self) -> None:
        fixtures = (
            (
                LEGACY_V2_AUTO_TOKEN,
                LEGACY_V2_AUTO_SHA256,
                LEGACY_V2_AUTO_READINGS_SHA256,
                ["spiral-tarot"],
                [35],
            ),
            (
                LEGACY_V2_DUAL_TOKEN,
                LEGACY_V2_DUAL_SHA256,
                LEGACY_V2_DUAL_READINGS_SHA256,
                ["symbolic-prompt", "spiral-tarot"],
                [60, 30],
            ),
        )
        for token, checksum, readings_checksum, selected, rolls in fixtures:
            with self.subTest(selected=selected):
                replayed = oracle.run_replay(token)
                self.assertEqual(
                    replayed["replay_payload_schema"], oracle.PREVIOUS_REPLAY_SCHEMA
                )
                self.assertEqual(
                    replayed["selection"]["selector_spec"], oracle.SELECTOR_SPEC_V2
                )
                self.assertEqual(replayed["replay"]["token"], token)
                self.assertEqual(replayed["replay"]["sha256"], checksum)
                self.assertEqual(replayed["selection"]["selected_backends"], selected)
                self.assertEqual(
                    [
                        step["roll_zero_based"]
                        for step in replayed["selection"]["steps"]
                    ],
                    rolls,
                )
                self.assertEqual(
                    hashlib.sha256(
                        oracle.canonical_json(replayed["readings"])
                    ).hexdigest(),
                    readings_checksum,
                )

    def test_precommit_tampering_fails_receipt_check(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[0, 1, 2]):
            live = run_live(
                focus="Precommit tamper check",
                mode="single",
                explicit_backend="symbolic-prompt",
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        payload = oracle.decode_replay_token(live["replay"]["token"])
        payload["precommit"]["prior_frame"] = "A different prior frame"
        tampered_token, _ = oracle.encode_replay_token(payload)
        with self.assertRaisesRegex(ValueError, "receipt checksum"):
            oracle.run_replay(tampered_token)

    def test_text_places_boundary_after_draw(self) -> None:
        with patch.object(oracle.secrets, "randbelow", side_effect=[0, 0]):
            live = run_live(
                focus="Text order check",
                mode="single",
                explicit_backend="spiral-tarot",
                overrides=[],
                timestamp_arg=FIXED_TIME,
            )
        text = oracle.format_text(live)
        self.assertTrue(text.startswith("Spiral Oracle\nFocus:"))
        self.assertLess(text.index("Prior frame:"), text.index("Backend:"))
        self.assertLess(text.index("Backend:"), text.index("Audit boundary:"))
        self.assertNotIn("Symbolic perturbation only", text)
        output_keys = list(live)
        self.assertLess(output_keys.index("precommit"), output_keys.index("readings"))
        self.assertLess(
            output_keys.index("readings"), output_keys.index("oracle_contract")
        )

    def test_cli_requires_full_precommit(self) -> None:
        completed = subprocess.run(
            [str(SCRIPT), "--focus", "Incomplete live draw"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--prior-frame", completed.stderr)

    def test_backend_listing_supports_text_format(self) -> None:
        completed = subprocess.run(
            [str(SCRIPT), "--list-backends", "--format", "text"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("spiral-iching: base 30, allowed 23..37", completed.stdout)
        self.assertIn("spiral-tarot: base 25, allowed 19..31", completed.stdout)
        self.assertIn(
            "spiral-western-astrology: base 20, allowed 15..25", completed.stdout
        )
        self.assertIn("spiral-four-pillars: base 15, allowed 12..18", completed.stdout)
        self.assertIn("symbolic-prompt: base 10, allowed 8..12", completed.stdout)
        self.assertEqual(completed.stderr, "")


class IChingBackendTests(unittest.TestCase):
    def test_three_coin_distribution_is_one_three_three_one(self) -> None:
        counts = {value: 0 for value in (6, 7, 8, 9)}
        for toss in itertools.product("HT", repeat=3):
            counts[iching.line_value("".join(toss))] += 1
        self.assertEqual(counts, {6: 1, 7: 3, 8: 3, 9: 1})

    def test_all_old_yang_changes_one_to_two(self) -> None:
        result = iching.cast(ALL_OLD_YANG)
        self.assertEqual(result["primary_hexagram"]["number"], 1)
        self.assertEqual(result["relating_hexagram"]["number"], 2)
        self.assertEqual(result["moving_lines"], [1, 2, 3, 4, 5, 6])

    def test_water_over_thunder_is_three_and_mapping_is_bijective(self) -> None:
        groups = ["HTT", "HHT", "HHT", "HHT", "HTT", "HHT"]
        result = iching.cast(groups)
        self.assertEqual(result["primary_hexagram"]["number"], 3)
        numbers = {
            iching.hexagram_number(bits) for bits in itertools.product((0, 1), repeat=6)
        }
        self.assertEqual(numbers, set(range(1, 65)))

    def test_imported_api_rejects_malformed_groups(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly three H/T"):
            iching.cast(["H"] * 6)

    def test_replay_pins_ruleset_version(self) -> None:
        payload = {
            "schema": iching.REPLAY_SCHEMA,
            "ruleset_version": iching.RULESET_VERSION,
            "coins_bottom_to_top": ALL_OLD_YANG,
        }
        self.assertEqual(
            iching.replay(payload, FIXED_TIME)["moving_lines"], list(range(1, 7))
        )
        payload["ruleset_version"] = "different/v9"
        with self.assertRaisesRegex(ValueError, "invalid I Ching"):
            iching.replay(payload, FIXED_TIME)


class TarotBackendTests(unittest.TestCase):
    def test_catalog_is_complete_unique_and_pins_boundaries(self) -> None:
        self.assertEqual(len(tarot.CARDS), 78)
        self.assertEqual(len({card["card_id"] for card in tarot.CARDS}), 78)
        self.assertEqual(sum(card["arcana"] == "major" for card in tarot.CARDS), 22)
        for suit in tarot.SUITS:
            self.assertEqual(sum(card["suit"] == suit for card in tarot.CARDS), 14)
        fixtures = {
            0: "The Fool",
            8: "Strength",
            11: "Justice",
            20: "Judgement",
            21: "The World",
            22: "Ace of Wands",
            35: "King of Wands",
            36: "Ace of Cups",
            49: "King of Cups",
            50: "Ace of Swords",
            63: "King of Swords",
            64: "Ace of Pentacles",
            77: "King of Pentacles",
        }
        for index, name in fixtures.items():
            self.assertEqual(tarot.CARDS[index]["name"], name)
        self.assertEqual(
            tarot.catalog_sha256(),
            "6c5f9bc8538ad0f7726c4293d1fea198b1e7b5c1f16e666365a09782f2997066",
        )

    def test_catalog_is_deeply_immutable(self) -> None:
        with self.assertRaises(TypeError):
            tarot.CARDS[0]["name"] = "MUTATED"  # type: ignore[index]

    def test_generate_uses_uniform_card_then_independent_orientation(self) -> None:
        with patch.object(
            tarot.secrets, "randbelow", side_effect=[77, 1]
        ) as random_draw:
            result, payload = tarot.generate(FIXED_TIME)
        self.assertEqual(random_draw.call_args_list, [call(78), call(2)])
        self.assertEqual(result["draw"]["card"]["name"], "King of Pentacles")
        self.assertEqual(result["draw"]["orientation"], "reversed")
        self.assertEqual(payload["card_index"], 77)
        self.assertEqual(payload["orientation_bit"], 1)

    def test_fixed_replay_is_timestamp_independent_and_exact(self) -> None:
        payload = {
            "schema": tarot.REPLAY_SCHEMA,
            "catalog_version": tarot.CATALOG_VERSION,
            "ruleset_version": tarot.RULESET_VERSION,
            "card_index": 8,
            "orientation_bit": 0,
        }
        with patch.object(
            tarot.secrets,
            "randbelow",
            side_effect=AssertionError("replay consumed randomness"),
        ):
            first = tarot.replay(payload, FIXED_TIME)
            second = tarot.replay(payload, "2030-01-01T00:00:00.000+00:00")
        self.assertEqual(first, second)
        self.assertEqual(first["draw"]["card"]["name"], "Strength")
        self.assertEqual(first["draw"]["orientation"], "upright")

    def test_replay_rejects_invalid_indices_and_versions(self) -> None:
        base = {
            "schema": tarot.REPLAY_SCHEMA,
            "catalog_version": tarot.CATALOG_VERSION,
            "ruleset_version": tarot.RULESET_VERSION,
            "card_index": 0,
            "orientation_bit": 0,
        }
        for bad_card in (-1, 78, True, 1.0, "1"):
            payload = {**base, "card_index": bad_card}
            with self.assertRaisesRegex(ValueError, "card_index"):
                tarot.replay(payload, FIXED_TIME)
        for bad_orientation in (-1, 2, True, "0"):
            payload = {**base, "orientation_bit": bad_orientation}
            with self.assertRaisesRegex(ValueError, "orientation_bit"):
                tarot.replay(payload, FIXED_TIME)
        with self.assertRaisesRegex(ValueError, "invalid Tarot"):
            tarot.replay({**base, "catalog_version": "unknown/v9"}, FIXED_TIME)
        for mutation in (
            {**base, "schema": "unknown/v9"},
            {**base, "ruleset_version": "unknown/v9"},
            {key: value for key, value in base.items() if key != "card_index"},
            {**base, "extra": 1},
            None,
        ):
            with self.assertRaisesRegex(ValueError, "invalid Tarot"):
                tarot.replay(mutation, FIXED_TIME)  # type: ignore[arg-type]

    def test_result_contains_no_verdict_or_recommendation_fields(self) -> None:
        result = tarot.render(0, 0)
        forbidden = {"meaning", "favorable", "prediction", "recommendation", "decision"}
        self.assertTrue(forbidden.isdisjoint(set(nested_keys(result))))


class WesternAstrologyBackendTests(unittest.TestCase):
    def test_os_timezone_and_uuidv7_thread_origin_are_pinned(self) -> None:
        self.assertEqual(
            _thread_origin.parse_zone_tab_coordinates("+340308-1181434"),
            (34_052_222, -118_242_778),
        )
        start = _thread_origin.uuid7_start_utc(FIXED_THREAD_ID)
        self.assertIsNotNone(start)
        assert start is not None
        self.assertEqual(
            start.isoformat(timespec="milliseconds"), "2025-06-01T12:34:56.789+00:00"
        )

        with patch.dict(
            os.environ,
            {"TZ": "America/Los_Angeles", "CODEX_THREAD_ID": FIXED_THREAD_ID},
            clear=True,
        ):
            origin = _thread_origin.capture_thread_origin()
            timezone_context = _thread_origin.capture_os_timezone_context(FIXED_TIME)
        self.assertTrue(origin["available"])
        self.assertEqual(origin["thread_start_local"], "2025-06-01T05:34:56.789-07:00")
        self.assertEqual(origin["timezone_id"], "America/Los_Angeles")
        self.assertEqual(
            origin["reference_point"]["coordinate_text"], "+340308-1181434"
        )
        self.assertEqual(origin["reference_point"]["latitude_microdegrees"], 34_052_222)
        self.assertEqual(
            origin["reference_point"]["longitude_microdegrees"], -118_242_778
        )
        self.assertTrue(timezone_context["available"])
        self.assertEqual(timezone_context["timezone_id"], "America/Los_Angeles")
        self.assertEqual(timezone_context["utc_offset_seconds"], -25_200)

    def test_missing_thread_id_degrades_without_inventing_an_origin(self) -> None:
        with patch.dict(os.environ, {"TZ": "America/Los_Angeles"}, clear=True):
            origin = _thread_origin.capture_thread_origin()
        self.assertFalse(origin["available"])
        self.assertIn("CODEX_THREAD_ID", origin["reason"])

    def test_julian_day_and_solar_fixture(self) -> None:
        j2000 = _solar.parse_moment("2000-01-01T12:00:00.000+00:00")
        self.assertEqual(_solar.julian_day_utc(j2000), 2_451_545.0)
        self.assertEqual(
            _solar.apparent_solar_longitude_millidegrees(FIXED_TIME), 156_582
        )
        equivalent_utc = "2026-08-29T22:04:05.123+00:00"
        self.assertEqual(
            _solar.apparent_solar_longitude_millidegrees(equivalent_utc), 156_582
        )

    def test_catalog_and_current_moment_fixture_are_pinned(self) -> None:
        self.assertEqual(len(western_astrology.SIGNS), 12)
        self.assertEqual(
            western_astrology.catalog_sha256(),
            "9e9b9a342682b07a6dfb978649cd40df10389d600173962ad15ece77ff2fda68",
        )
        with self.assertRaises(TypeError):
            western_astrology.SIGNS[0]["name"] = "MUTATED"  # type: ignore[index]
        with patch.dict(
            os.environ,
            {"TZ": "America/Los_Angeles", "CODEX_THREAD_ID": FIXED_THREAD_ID},
            clear=True,
        ):
            result, payload = western_astrology.generate(FIXED_TIME)
        self.assertEqual(result["oracle_moment_sun"]["sign"]["name"], "Virgo")
        self.assertEqual(result["oracle_moment_sun"]["degree_within_sign"], "6.582")
        self.assertEqual(
            payload["oracle_moment_solar_longitude_millidegrees"],
            result["oracle_moment_sun"]["longitude_millidegrees"],
        )
        thread_sun = result["thread_nativity_sun"]
        self.assertTrue(thread_sun["available"])
        self.assertEqual(thread_sun["sign"]["name"], "Gemini")
        self.assertEqual(thread_sun["degree_within_sign"], "11.277")
        self.assertEqual(payload["thread_start_solar_longitude_millidegrees"], 71_277)
        self.assertFalse(thread_sun["coordinates_used_for_solar_longitude"])
        self.assertNotIn(FIXED_THREAD_ID, json.dumps(payload))

    def test_replay_is_timestamp_bound_and_rejects_bad_shapes(self) -> None:
        with patch.dict(
            os.environ,
            {"TZ": "America/Los_Angeles", "CODEX_THREAD_ID": FIXED_THREAD_ID},
            clear=True,
        ):
            payload = western_astrology.replay_payload_for(FIXED_TIME)
        with patch.dict(os.environ, {}, clear=True):
            first = western_astrology.replay(payload, FIXED_TIME)
            second = western_astrology.replay(dict(payload), FIXED_TIME)
        self.assertEqual(first, second)
        for mutation in (
            {**payload, "oracle_moment_solar_longitude_millidegrees": 0},
            {**payload, "thread_start_solar_longitude_millidegrees": 0},
            {**payload, "catalog_version": "unknown/v9"},
            {key: value for key, value in payload.items() if key != "ruleset_version"},
            {**payload, "extra": 1},
            None,
        ):
            with self.assertRaisesRegex(ValueError, "Western astrology"):
                western_astrology.replay(mutation, FIXED_TIME)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "does not match timestamp"):
            western_astrology.replay(payload, "2026-08-30T15:04:05.123-07:00")

        tampered_context = json.loads(json.dumps(payload))
        tampered_context["thread_origin"]["utc_offset_seconds"] = 0
        with self.assertRaisesRegex(ValueError, "replay context"):
            western_astrology.replay(tampered_context, FIXED_TIME)

    def test_supported_range_and_semantic_omissions(self) -> None:
        with self.assertRaisesRegex(ValueError, "1901 through 2099"):
            western_astrology.generate("2100-01-01T00:00:00.000+00:00")
        result, _ = western_astrology.generate(FIXED_TIME)
        forbidden = {"meaning", "favorable", "prediction", "recommendation", "decision"}
        self.assertTrue(forbidden.isdisjoint(set(nested_keys(result))))
        self.assertIn(
            "houses and Ascendant", result["method"]["spiral_conventions"]["omitted"]
        )


class FourPillarsBackendTests(unittest.TestCase):
    def test_catalog_cycle_and_hash_are_pinned(self) -> None:
        self.assertEqual(len(four_pillars.STEMS), 10)
        self.assertEqual(len(four_pillars.BRANCHES), 12)
        self.assertEqual(
            four_pillars.catalog_sha256(),
            "ccaae2a8fd3dc19e60b72a7007340170c06ef2d79afde4ada9ba9f1dc2165cd3",
        )
        with self.assertRaises(TypeError):
            four_pillars.STEMS[0]["han"] = "X"  # type: ignore[index]
        self.assertEqual(
            [
                four_pillars.pillar(i % 10, i % 12)["sexagenary_index_zero_based"]
                for i in range(60)
            ],
            list(range(60)),
        )
        with self.assertRaisesRegex(ValueError, "parity"):
            four_pillars.sexagenary_index(0, 1)

    def test_official_almanac_date_fixtures(self) -> None:
        fixtures = {
            FIXED_TIME: {
                "year": "Bing-Wu",
                "month": "Bing-Shen",
                "day": "Yi-Hai",
                "hour": "Jia-Shen",
            },
            "2024-02-10T12:00:00.000+08:00": {
                "year": "Jia-Chen",
                "month": "Bing-Yin",
                "day": "Jia-Chen",
                "hour": "Geng-Wu",
            },
        }
        for timestamp, expected in fixtures.items():
            with self.subTest(timestamp=timestamp):
                result, _ = four_pillars.generate(timestamp)
                self.assertEqual(
                    {name: value["latin"] for name, value in result["pillars"].items()},
                    expected,
                )

    def test_li_chun_and_civil_hour_boundaries_are_explicit(self) -> None:
        before, _ = four_pillars.generate("2026-02-03T12:00:00.000+08:00")
        after, _ = four_pillars.generate("2026-02-05T12:00:00.000+08:00")
        self.assertEqual(before["pillars"]["year"]["latin"], "Yi-Si")
        self.assertEqual(before["pillars"]["month"]["latin"], "Ji-Chou")
        self.assertEqual(after["pillars"]["year"]["latin"], "Bing-Wu")
        self.assertEqual(after["pillars"]["month"]["latin"], "Geng-Yin")

        at_2259, _ = four_pillars.generate("2026-08-29T22:59:00.000+08:00")
        at_2300, _ = four_pillars.generate("2026-08-29T23:00:00.000+08:00")
        at_midnight, _ = four_pillars.generate("2026-08-30T00:00:00.000+08:00")
        self.assertEqual(at_2259["pillars"]["hour"]["latin"], "Ding-Hai")
        self.assertEqual(at_2300["pillars"]["day"]["latin"], "Yi-Hai")
        self.assertEqual(at_2300["pillars"]["hour"]["latin"], "Bing-Zi")
        self.assertEqual(at_midnight["pillars"]["day"]["latin"], "Bing-Zi")
        self.assertEqual(at_midnight["pillars"]["hour"]["latin"], "Wu-Zi")

    def test_os_offset_basis_changes_local_pillars_but_not_solar_longitude(
        self,
    ) -> None:
        west = "2026-08-29T23:30:00.000-07:00"
        east = "2026-08-30T15:30:00.000+09:00"
        west_result, _ = four_pillars.generate(west)
        east_result, _ = four_pillars.generate(east)
        self.assertEqual(
            west_result["calendar_primitives"]["solar_longitude_millidegrees"],
            east_result["calendar_primitives"]["solar_longitude_millidegrees"],
        )
        self.assertNotEqual(
            west_result["pillars"]["day"]["latin"],
            east_result["pillars"]["day"]["latin"],
        )

    def test_replay_is_timestamp_bound_and_contains_no_verdict(self) -> None:
        payload = four_pillars.replay_payload_for(FIXED_TIME)
        result = four_pillars.replay(payload, FIXED_TIME)
        self.assertEqual(result, four_pillars.replay(dict(payload), FIXED_TIME))
        for mutation in (
            {**payload, "local_civil_date": "2026-08-30"},
            {**payload, "ruleset_version": "unknown/v9"},
            {
                key: value
                for key, value in payload.items()
                if key != "utc_offset_seconds"
            },
            {**payload, "extra": 1},
            None,
        ):
            with self.assertRaisesRegex(ValueError, "Four Pillars"):
                four_pillars.replay(mutation, FIXED_TIME)  # type: ignore[arg-type]
        forbidden = {"meaning", "favorable", "prediction", "recommendation", "decision"}
        self.assertTrue(forbidden.isdisjoint(set(nested_keys(result))))


class SymbolicPromptBackendTests(unittest.TestCase):
    def test_fixed_replay_is_deterministic_and_discloses_authorship(self) -> None:
        payload = {
            "schema": symbolic_prompt.REPLAY_SCHEMA,
            "catalog_version": symbolic_prompt.CATALOG_VERSION,
            "symbol_index": 0,
            "motion_index": 1,
            "lens_index": 2,
        }
        first = symbolic_prompt.replay(payload, FIXED_TIME)
        second = symbolic_prompt.replay(payload, FIXED_TIME)
        self.assertEqual(first, second)
        self.assertIn("authored", first["method"]["authorship_disclosure"])

    def test_replay_indices_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "symbol_index"):
            symbolic_prompt.replay(
                {
                    "schema": symbolic_prompt.REPLAY_SCHEMA,
                    "catalog_version": symbolic_prompt.CATALOG_VERSION,
                    "symbol_index": True,
                    "motion_index": 0,
                    "lens_index": 0,
                },
                FIXED_TIME,
            )
        with self.assertRaisesRegex(ValueError, "lens_index"):
            symbolic_prompt.replay(
                {
                    "schema": symbolic_prompt.REPLAY_SCHEMA,
                    "catalog_version": symbolic_prompt.CATALOG_VERSION,
                    "symbol_index": 0,
                    "motion_index": 0,
                    "lens_index": 99,
                },
                FIXED_TIME,
            )


if __name__ == "__main__":
    unittest.main()
