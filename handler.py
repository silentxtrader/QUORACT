#!/usr/bin/env python3
"""Minimal QUORACT v0.9 conformance handler."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

WIRE_FIELDS = {"object", "intent", "authority", "lifetime", "result"}


def load_capabilities():
    with Path(__file__).with_name("capabilities.json").open(encoding="utf-8") as f:
        return json.load(f)["capabilities"]


def parse_datetime(value):
    if not isinstance(value, str):
        raise ValueError("date-time must be a string")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    datetime.fromisoformat(value)


def validate_data(data, capability):
    if not isinstance(data, dict):
        raise ValueError("data must be an object")
    required = set(capability["required_data"])
    if not required.issubset(data):
        raise ValueError("missing required data")
    if not capability.get("additional_data", False) and set(data) != required:
        raise ValueError("unexpected additional data")
    for key in capability.get("date_time_data", []):
        parse_datetime(data[key])


def validate_opaque(value, capability, kind):
    if not isinstance(value, dict):
        raise ValueError(f"{kind} must be an object")
    if not value:
        return
    if set(value) - {"type", "data"}:
        raise ValueError(f"{kind} has unexpected fields")
    if "type" not in value or "data" not in value:
        raise ValueError(f"{kind} must contain type and data")
    if value["type"] != capability[f"{kind}_type"]:
        raise ValueError(f"{kind} type mismatch")
    validate_data(value["data"], capability)


def validate(envelope):
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be an object")
    if set(envelope) != WIRE_FIELDS:
        raise ValueError("envelope must contain exactly the wire fields")

    intent = envelope["intent"]
    if not isinstance(intent, dict) or set(intent) != {"action"}:
        raise ValueError("intent must contain exactly action")
    action = intent["action"]
    capability = next((c for c in load_capabilities() if c["intent"] == action), None)
    if capability is None:
        raise ValueError("unknown action")

    validate_opaque(envelope["object"], capability, "object")
    validate_opaque(envelope["result"], capability, "result")

    authority = envelope["authority"]
    if not isinstance(authority, dict) or set(authority) != {"scheme", "scope"}:
        raise ValueError("authority must contain exactly scheme and scope")
    if not isinstance(authority["scheme"], str):
        raise ValueError("authority scheme must be a string")
    if not isinstance(authority["scope"], list) or not all(isinstance(s, str) for s in authority["scope"]):
        raise ValueError("authority scope must be an array of strings")

    lifetime = envelope["lifetime"]
    if not isinstance(lifetime, dict) or set(lifetime) != {"expires_at", "max_uses"}:
        raise ValueError("lifetime must contain exactly expires_at and max_uses")
    parse_datetime(lifetime["expires_at"])
    if not isinstance(lifetime["max_uses"], int) or isinstance(lifetime["max_uses"], bool) or lifetime["max_uses"] < 1:
        raise ValueError("max_uses must be a positive integer")


def read_envelope(argument):
    try:
        path = Path(argument)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    except OSError:
        pass
    return argument


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--envelope", required=True)
    args = parser.parse_args()
    try:
        validate(json.loads(read_envelope(args.envelope)))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
