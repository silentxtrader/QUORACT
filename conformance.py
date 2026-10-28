#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, subprocess, sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
# Conservative CLI budget limit, not a protocol lifetime or a default timeout.
MAX_TIMEOUT_SECONDS = 86400

def absolute_uri(value: object) -> bool:
    return isinstance(value, str) and bool(urlparse(value).scheme)

def positive_timeout(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f'timeout must be a positive finite number at most {MAX_TIMEOUT_SECONDS}') from None
    if not math.isfinite(seconds) or not 0 < seconds <= MAX_TIMEOUT_SECONDS:
        raise argparse.ArgumentTypeError(f'timeout must be a positive finite number at most {MAX_TIMEOUT_SECONDS}')
    return seconds


def call(handler: Path, vector: Path, timeout_seconds: float | None = None):
    try:
        return subprocess.run([str(handler), '--envelope', str(vector)],
                              text=True, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        fail(f"handler timed out after {timeout_seconds:g} seconds: {vector}")

def fail(msg: str):
    raise AssertionError(msg)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--handler', required=True)
    ap.add_argument('--timeout-seconds', type=positive_timeout,
                    help='optional per-vector handler timeout in seconds, 0 < value <= 86400 (default: no timeout)')
    args = ap.parse_args()
    handler = Path(args.handler).resolve()
    expectations = json.loads((ROOT / 'expectations.json').read_text())
    passed = 0

    for case in expectations['positive']:
        vector = ROOT / case['file']
        request = json.loads(vector.read_text())
        p = (call(handler, vector) if args.timeout_seconds is None
             else call(handler, vector, args.timeout_seconds))
        if p.returncode != 0:
            fail(f"positive vector rejected: {case['file']}\nstdout={p.stdout}\nstderr={p.stderr}")
        try:
            out = json.loads(p.stdout)
        except Exception as exc:
            fail(f"positive vector returned invalid JSON: {case['file']}: {exc}")
        if out.get('status') != 'ok': fail(f"missing status=ok: {case['file']}")
        if out.get('binding_mode') != case['binding_mode']: fail(f"wrong binding mode: {case['file']}")
        if out.get('object_type') != request['object']['type']: fail(f"wrong object type: {case['file']}")
        if out.get('intent') != request['intent']['action']: fail(f"wrong intent: {case['file']}")
        if out.get('result_type') != case['result_type']: fail(f"wrong result type: {case['file']}")
        result = out.get('result')
        if not isinstance(result, dict): fail(f"result must be object: {case['file']}")
        if case.get('preserve_object_data'):
            if result.get('@type') != case['result_type']: fail(f"external result @type mismatch: {case['file']}")
            if '@id' in result and not absolute_uri(result['@id']): fail(f"result @id is not absolute URI: {case['file']}")
            for k, v in request['object']['data'].items():
                if result.get(k) != v: fail(f"semantic property not preserved: {k} in {case['file']}")
        required = case.get('requires_result_key')
        if required and (not isinstance(result.get(required), str) or not result[required]):
            fail(f"missing non-empty result key {required}: {case['file']}")
        passed += 1
        print(f"PASS positive {case['file']}")

    for case in expectations['negative']:
        vector = ROOT / case['file']
        p = (call(handler, vector) if args.timeout_seconds is None
             else call(handler, vector, args.timeout_seconds))
        if p.returncode == 0:
            fail(f"negative vector accepted: {case['file']}\nstdout={p.stdout}")
        passed += 1
        print(f"PASS negative {case['file']}")

    print(f"PASS v0.9 clean-room proxy conformance: {passed} vectors")
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
