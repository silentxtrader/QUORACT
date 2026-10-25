# QUORACT v0.9 public profile

Normative words MUST, MUST NOT, SHOULD, and MAY apply only to this research conformance gate.

## 1. Envelope

A request MUST be a JSON object with exactly five top-level members:

1. `object`
2. `intent`
3. `authority`
4. `lifetime`
5. `result`

No sixth top-level member is permitted by this profile.

`object` MUST be an object containing `type` and `data`. `object.type` MUST be an absolute URI string. `object.data` MUST be an object.

`intent` MUST be an object containing `action`, which MUST be an absolute URI string.

`authority` MUST be an object. This clean-room gate treats its internal authorization scheme as opaque; it does not replace the previously accepted authority model.

`lifetime` MUST be an object. This clean-room gate treats its internal lifetime/replay semantics as opaque; it does not replace the previously accepted lifetime model.

`result` MUST be an object containing `expects`, which MUST be an absolute URI string.

Wherever an object is required, an empty JSON object `{}` is valid unless required members are specified. A JSON array `[]` is never a JSON object. In particular, `authority: {}` and `lifetime: {}` are valid; arrays in either field MUST be rejected.

## 2. Capability matching

A handler MUST match capabilities by the exact triple:

`object.type + intent.action -> result.expects`

No local-name, prefix, suffix, fragment, scheme, HTTP/HTTPS, redirect, or version inference is allowed. A non-listed triple MUST fail closed.

Semantic identity and a handler's internal validation representation are independent. An implementer is free to use structs, code, JSON Schema, another schema system, or explicit validation logic internally. The wire MUST NOT carry that local schema identity as an extra top-level field.

## 3. Supported triples for this gate

### A. Schema.org calendar fixture

- object: `https://schema.org/Event`
- intent: `https://schema.org/ScheduleAction`
- result: `https://schema.org/Event`
- binding mode: `external-vocabulary`

`object.data` MUST contain exactly these properties, each with a non-empty string value:

- `https://schema.org/name`
- `https://schema.org/startDate`
- `https://schema.org/endDate`

`startDate` and `endDate` MUST parse as RFC 3339 date-times.

For the conformance adapter, a successful `result` MUST contain `@type` equal to the expected result URI and MUST preserve the three semantic input properties and values. It MAY contain an implementation-local absolute `@id`.

### B. W3C ActivityStreams note fixture

- object: `https://www.w3.org/ns/activitystreams#Note`
- intent: `https://www.w3.org/ns/activitystreams#Create`
- result: `https://www.w3.org/ns/activitystreams#Note`
- binding mode: `external-vocabulary`

`object.data` MUST contain exactly one property:

- `https://www.w3.org/ns/activitystreams#content`

Its value MUST be a non-empty string.

For the conformance adapter, a successful `result` MUST contain `@type` equal to the expected result URI and MUST preserve the semantic input property and value. It MAY contain an implementation-local absolute `@id`.

### C. Retained v0.7 Calendar direct-schema-ID fixture

- object: `https://example.org/semantic/calendar/event/1`
- intent: `https://example.org/semantic/calendar/create/1`
- result: `https://example.org/semantic/calendar/created/1`
- binding mode: `direct-schema-id`

`object.data` MUST contain exactly `title`, `start`, and `end`, all non-empty strings. `start` and `end` MUST parse as RFC 3339 date-times.

For the conformance adapter, a successful result MUST contain a non-empty string `event_id`.

## 4. Failure behavior

A handler MUST reject:

- any envelope whose top-level member set is not exactly the five required names;
- missing or non-object nested structures described above;
- non-absolute semantic identifiers;
- any semantic triple not listed in the capability table;
- payloads that violate the selected capability's structural requirements;
- result expectations that do not exactly match a supported triple.

Failures MUST be closed: the handler MUST NOT silently repair, alias, downgrade, or guess identifiers or payloads.

## 5. External vocabulary handling

External vocabulary URIs are identifiers, not a requirement to dereference the Web during execution. This gate MUST be runnable offline after source/toolchain setup. The handler MUST NOT require a central semantic registry.

This kit uses canonical vocabulary identifiers already established outside QUORACT. It does not claim ownership of Schema.org or W3C namespaces.

## 6. Scope limits

This kit intentionally does not standardize network transport, discovery protocol, production authorization/signature format, namespace ownership continuity, schema distribution, universal semantic equivalence, or a public standards process. Those remain separate research questions.
