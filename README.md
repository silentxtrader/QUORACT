# QUORACT

A small JSON format for describing actions.

Each request has five top-level fields: `object`, `intent`, `authority`, `lifetime`, and `result`.

```json
{
  "object": {
    "type": "https://www.w3.org/ns/activitystreams#Note",
    "data": {
      "https://www.w3.org/ns/activitystreams#content": "Hello"
    }
  },
  "intent": {"action": "https://www.w3.org/ns/activitystreams#Create"},
  "authority": {},
  "lifetime": {},
  "result": {"expects": "https://www.w3.org/ns/activitystreams#Note"}
}
```

## Try it

Read [SPEC.md](SPEC.md) and [capabilities.json](capabilities.json). Write a handler in any language:

```sh
handler --envelope /path/to/request.json
```

Run the public tests:

```sh
python3 conformance.py --handler /absolute/path/to/handler
```

The kit includes 4 valid and 12 invalid test cases. There is no reference handler here.
Calendar negatives independently exercise invalid `start` and `end` date-times in both
calendar bindings: an out-of-range month and a missing UTC offset, respectively.
Each date-time case otherwise matches its positive calendar fixture.

Run the maintainer checks for vector registration, isolated invalid date-times, and
runner acceptance/rejection behavior with Python's standard library:

```sh
python3 -B -m unittest discover -s tests -v
```

These checks use fixture process results, not a handler implementation. They do not
replace running `conformance.py` against an independent handler.

## Scope

This is the experimental **v0.9 public profile**. The `authority` and `lifetime` fields are opaque and **not enforced** by this kit. Passing these tests does not establish real authorization, expiry enforcement, replay protection, production security, or compatibility with other implementations.

## License

[Apache-2.0](LICENSE). Free to use, modify, and distribute, including commercially, under its terms. The license does not grant trademark rights.

Maintained by neevan.
