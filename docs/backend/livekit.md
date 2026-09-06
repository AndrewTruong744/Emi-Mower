# LiveKit stream credentials

The backend does not receive, relay, record, or render video. It generates
short-lived LiveKit access tokens after Zenoh ACLs have constrained the caller
to a mower-specific route. LiveKit transports the actual media stream.

## Rooms and token lifetime

Each mower uses its mower UUID as the LiveKit room name. Both token types have
a one-hour lifetime and return the configured `LIVEKIT_URL`, JWT token, and
expiry. Configuration comes from `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and
`LIVEKIT_API_SECRET`; keep the API secret out of source control and mobile
builds.

## Mower upload flow

```text
mower mTLS session → mower/{mower_id}/livekit/upload query
  → backend issues publish-only room token → mower connects to LiveKit
  → mower publishes media to room {mower_id}
```

The token identity is the mower ID. Its grant allows room join and publishing,
but not subscribing. The mTLS router ACL limits the mower certificate to its
own route before the backend issues a token.

## App viewer flow

```text
authenticated app session → mower/{mower_id}/livekit/consume query
  → backend issues subscribe-only room token → app connects to LiveKit
  → app subscribes to media from room {mower_id}
```

Each viewer receives a random `consumer-{uuid}` identity. Its grant allows room
join and subscribing, but not publishing. The user-specific app-router ACL
limits the request to mowers owned by that user. The mobile UI currently obtains
and manages viewer credentials; attaching a native video renderer is a separate
client integration task.

## Failure and security behavior

The LiveKit service wraps token-generation failures as a typed backend error,
which the Zenoh query handler returns as a structured error reply. Do not log
the API secret or issued JWTs. Token grants are deliberately least-privilege;
do not combine publisher and viewer capabilities without a separate reviewed
requirement.
