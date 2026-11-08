#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent

def absolute_uri(value: object) -> bool:
    if not isinstance(value, str):
        return False
    # urlparse can strip controls; validate the original identifier first.
    if any(ord(char) <= 0x20 or ord(char) == 0x7f for char in value):
        return False
    return bool(urlparse(value).scheme)

def call(handler: Path, vector: Path):
    return subprocess.run([str(handler), '--envelope', str(vector)], text=True, capture_output=True)

def fail(msg: str):
    raise AssertionError(msg)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--handler', required=True)
    args = ap.parse_args()
    handler = Path(args.handler).resolve()
    expectations = json.loads((ROOT / 'expectations.json').read_text())
    passed = 0

    for case in expectations['positive']:
        vector = ROOT / case['file']
        request = json.loads(vector.read_text())
        p = call(handler, vector)
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
        p = call(handler, vector)
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
