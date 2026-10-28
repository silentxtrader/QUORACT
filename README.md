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

To limit each handler invocation, optionally add `--timeout-seconds 5` (any
positive finite number of seconds up to 86400, or 24 hours). Larger values
are rejected before starting the handler to avoid platform timer overflow; this
is a conservative runner input limit, not a protocol deadline. The default has no timeout. A timed-out
handler fails the runner, including for negative vectors; it does not count as
successful rejection. This limit applies to the direct handler process, not a
sandbox for its descendants, and does not enforce the request's `lifetime`.

Run the runner's regression tests with Python's standard library:

```sh
python3 -m unittest discover -s tests -v
```

The kit includes 4 valid and 8 invalid test cases. There is no reference handler here.

## Scope

This is the experimental **v0.9 public profile**. The `authority` and `lifetime` fields are opaque and **not enforced** by this kit. Passing these tests does not establish real authorization, expiry enforcement, replay protection, production security, or compatibility with other implementations.

## License

[Apache-2.0](LICENSE). Free to use, modify, and distribute, including commercially, under its terms. The license does not grant trademark rights.

Maintained by neevan.
