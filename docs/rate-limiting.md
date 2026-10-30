# Rate limiting

Status: implemented.

The API is public and every analysis spends a paid provider key. Limits are per client IP
with a shared store, plus one global daily analysis budget. A request that is over the
limit is refused before its body is read.

## Policy

| Scope | Method and path | Limit | Window |
| --- | --- | --- | --- |
| Analyses, per IP | `POST /api/v1/analyses` | 10 | 3600 s |
| Extracts, per IP | `POST /api/v1/documents/extract` | 30 | 3600 s |
| Any other request, per IP | any other non-health path | 120 | 60 s |
| Analyses, all IPs | `POST /api/v1/analyses` | 300 | 86400 s |

Exempt: `GET /api/v1/health`, `GET /health`, and every `OPTIONS` request, so CORS
preflight never consumes budget.

The global budget is checked after the per-IP limit. A caller already over its own limit
does not spend the daily budget.

## Client identity

Order of trust:

1. `x-real-ip`. Vercel sets it and overwrites `x-forwarded-for`, so a spoofed value does
   not reach the app.
2. The last non-empty entry of `x-forwarded-for`. Empty entries are skipped.
3. The socket peer, used locally and in tests.

Raw addresses are never stored. Keys look like `rl:analyses:<64 hex chars>`, where the
digest is `HMAC-SHA256(RATE_LIMIT_SALT, ip)`. An operator who has the salt can test one
address, so keep the salt private.

## Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `UPSTASH_REDIS_REST_URL` | empty | REST endpoint of the Redis database |
| `UPSTASH_REDIS_REST_TOKEN` | empty | REST token, read as a secret |
| `RATE_LIMIT_SALT` | empty | salt for the IP digest; empty uses a public fixed value |
| `RATE_LIMIT_ENABLED` | `true` | turn the limiter off |
| `RATE_LIMIT_ANALYSES_PER_HOUR` | `10` | per-IP analyses, 1 hour window |
| `RATE_LIMIT_EXTRACTS_PER_HOUR` | `30` | per-IP extracts, 1 hour window |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `120` | per-IP other requests, 1 minute window |
| `RATE_LIMIT_GLOBAL_ANALYSES_PER_DAY` | `300` | analyses across all IPs, 1 day window |

A URL without a token fails settings validation at startup. Both values are required
before the shared store is used.

## Upstash setup through the Vercel Marketplace

1. Open the project in Vercel, then Storage or Integrations, then the Marketplace.
2. Add Upstash Redis and create a database in the same region as the functions.
3. Connect the database to the project. Vercel writes the REST URL and token into the
   project environment.
4. Check the variable names the integration created. The app reads
   `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`. If the integration used
   different names, add these two as aliases in Project Settings, Environment Variables.
5. Set `RATE_LIMIT_SALT` to a private random string.
6. Redeploy. The startup log must not contain the memory-mode warning.

The token is a write-capable secret. Do not put it in any `VITE_` variable or in the
frontend.

## Store behaviour

`UpstashCounter` makes one REST call per decision. It posts a pipeline of three commands:
`INCR`, `EXPIRE <window> NX`, and `TTL`. The window is fixed: a key expires one window
after its first hit. `TTL` makes `RateLimit-Reset` accurate. If Redis reports no TTL the
window is used instead.

The pipeline body is a JSON array:

```json
[["INCR", "rl:analyses:..."], ["EXPIRE", "rl:analyses:...", 3600, "NX"], ["TTL", "rl:analyses:..."]]
```

A non-2xx answer, a transport error, an error entry, or a short pipeline raises a store
error. The limiter then uses the memory counter for that request, logs one warning, and
adds `X-RateLimit-Degraded: 1` to the response. The request still succeeds. The limiter
never fails a request because the store is down.

## Memory mode

With no store configured the limiter uses an in-process dict guarded by an asyncio lock.
It logs one startup warning that the limit is per instance.

It covers bursts against a single process. It does not survive a restart, a cold start, or
a second Vercel instance. Effective limits multiply by the number of instances, so the
shared store is required in production.

The older in-process guard of two concurrent POSTs remains. It bounds memory and provider
concurrency per instance. It is not a rate limit and does not replace this one.

## Response headers

On an allowed request:

```text
RateLimit-Limit: 10
RateLimit-Remaining: 7
RateLimit-Reset: 2741
```

`RateLimit-Reset` is seconds until the window ends. A 429 adds `Retry-After` with the same
value. A degraded decision adds `X-RateLimit-Degraded: 1`.

## The 429 shape

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 2741
RateLimit-Limit: 10
RateLimit-Remaining: 0
RateLimit-Reset: 2741
Content-Type: application/json
```

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Try again later.",
    "retryable": true
  },
  "request_id": "7c1d2f7e-0d4f-4a4e-9a5e-2b9f0f8f1a11"
}
```

The body uses the same envelope as every other error. `request_id` identifies the call in
logs.

## Order in the request

`RateLimitMiddleware` is the outermost middleware, ahead of `RequestBoundary`. A denied
POST is answered before any body byte is buffered, so an over-limit caller cannot make the
app hold a 4 MB upload.

## Tests

- `tests/unit/test_rate_limit.py` covers the pipeline command shape, the memory counter
  window, the policy table, the IP source order, and the hashed keys.
- `tests/integration/test_rate_limit_middleware.py` covers allow then deny at the
  boundary, the headers, the 429 body, the global cap, health and OPTIONS exemptions,
  spoofed `x-forwarded-for`, the degraded fallback, and disabled mode.

Upstash answers come from `httpx.MockTransport`. No test reaches the network.
