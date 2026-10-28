"""Corpus/runner checks, not a reference handler or an RFC 3339 parser."""

import contextlib
import copy
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
from unittest.mock import patch

import conformance


ROOT = Path(__file__).resolve().parents[1]

# Hand-checked invalid values: month 13 cannot be a calendar month;
# a local date-time without Z or a numeric UTC offset is not RFC 3339.
# Each request must otherwise be identical to its existing positive control.
CALENDAR_CASES = (
    (
        "schemaorg-calendar-invalid-start.json", "schemaorg-calendar.json",
        "https://schema.org/startDate", "2026-13-15T09:00:00+02:00",
    ),
    (
        "schemaorg-calendar-invalid-end.json", "schemaorg-calendar.json",
        "https://schema.org/endDate", "2026-09-15T09:30:00",
    ),
    (
        "v07-calendar-invalid-start.json", "v07-calendar.json",
        "start", "2026-13-11T09:00:00Z",
    ),
    (
        "v07-calendar-invalid-end.json", "v07-calendar.json",
        "end", "2026-09-11T09:30:00",
    ),
)

# Literal response metadata, independent of expectations.json. This only
# replays successful fixture responses at the external-process boundary.
POSITIVE_RESPONSES = {
    "schemaorg-calendar.json": ("external-vocabulary", "https://schema.org/Event"),
    "activitystreams-note.json": (
        "external-vocabulary", "https://www.w3.org/ns/activitystreams#Note",
    ),
    "v07-calendar.json": (
        "direct-schema-id", "https://example.org/semantic/calendar/created/1",
    ),
    "empty-opaque-objects.json": (
        "external-vocabulary", "https://www.w3.org/ns/activitystreams#Note",
    ),
}


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text())


def fixture_process_result(vector, accepted_negative=None):
    relative_path = vector.relative_to(ROOT).as_posix()
    if relative_path == accepted_negative:
        return subprocess.CompletedProcess([], 0, "{}", "")
    if relative_path.startswith("vectors/negative/"):
        return subprocess.CompletedProcess([], 1, "", "fixture rejection")
    binding_mode, result_type = POSITIVE_RESPONSES[vector.name]
    request = json.loads(vector.read_text())
    if binding_mode == "direct-schema-id":
        result = {"event_id": "fixture-event-id"}
    else:
        result = {"@type": result_type, **request["object"]["data"]}
    response = {
        "status": "ok",
        "binding_mode": binding_mode,
        "object_type": request["object"]["type"],
        "intent": request["intent"]["action"],
        "result_type": result_type,
        "result": result,
    }
    return subprocess.CompletedProcess([], 0, json.dumps(response), "")


class VectorTests(unittest.TestCase):
    def setUp(self):
        self.expectations = load_json("expectations.json")

    def test_manifest_covers_every_vector_once_in_the_correct_category(self):
        for category in ("positive", "negative"):
            with self.subTest(category=category):
                registered = [case["file"] for case in self.expectations[category]]
                on_disk = {
                    path.relative_to(ROOT).as_posix()
                    for path in (ROOT / "vectors" / category).glob("*.json")
                }
                self.assertEqual(len(registered), len(set(registered)))
                self.assertEqual(set(registered), on_disk)
                for path in registered:
                    request = load_json(path)
                    # Negative fixtures may intentionally have a non-object root.
                    if category == "positive":
                        self.assertIsInstance(request, dict)

    def test_manifest_allows_top_level_arrays_in_negative_vectors(self):
        original_load_json = load_json

        def load_with_negative_array(relative_path):
            if relative_path == "vectors/negative/array-instead-of-object.json":
                return []
            return original_load_json(relative_path)

        with patch(__name__ + ".load_json", side_effect=load_with_negative_array):
            self.test_manifest_covers_every_vector_once_in_the_correct_category()

    def test_each_calendar_field_has_a_registered_invalid_datetime(self):
        negatives = [case["file"] for case in self.expectations["negative"]]
        for filename, _, _, _ in CALENDAR_CASES:
            with self.subTest(vector=filename):
                self.assertEqual(negatives.count("vectors/negative/" + filename), 1)

    def test_invalid_datetimes_are_isolated_from_structural_failures(self):
        for filename, positive, field, invalid_value in CALENDAR_CASES:
            with self.subTest(vector=filename):
                path = "vectors/negative/" + filename
                self.assertTrue((ROOT / path).is_file(), path)
                request = load_json(path)
                control = load_json("vectors/positive/" + positive)
                self.assertEqual(request["object"]["data"][field], invalid_value)
                repaired = copy.deepcopy(request)
                repaired["object"]["data"][field] = control["object"]["data"][field]
                self.assertEqual(repaired, control)

    def run_runner(self, accepted_negative=None):
        def process_result(_handler, vector):
            return fixture_process_result(vector, accepted_negative)

        output = io.StringIO()
        with patch.object(sys, "argv", ["conformance.py", "--handler", "fixture-only"]), \
                patch.object(conformance, "call", side_effect=process_result), \
                contextlib.redirect_stdout(output):
            result = conformance.main()
        return result, output.getvalue()

    def test_runner_accepts_control_responses_and_negative_rejections(self):
        result, output = self.run_runner()
        self.assertEqual(result, 0)
        total = sum(len(cases) for cases in self.expectations.values())
        self.assertIn(f"PASS v0.9 clean-room proxy conformance: {total} vectors", output)

    def test_runner_fails_if_any_new_invalid_datetime_is_accepted(self):
        for filename, _, _, _ in CALENDAR_CASES:
            with self.subTest(vector=filename):
                path = "vectors/negative/" + filename
                with self.assertRaisesRegex(
                    AssertionError, "negative vector accepted: " + re.escape(path)
                ):
                    self.run_runner(accepted_negative=path)


if __name__ == "__main__":
    unittest.main()
