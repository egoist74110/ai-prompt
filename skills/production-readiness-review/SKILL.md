---
name: production-readiness-review
description: Pre-ship ops checklist for backend features — timeout, retry, circuit breaker, idempotency, monitoring, and failure recovery. Run before declaring a backend feature production-ready.
---

# Production Readiness Review

Catches the gap between "works in dev" and "survives production." Most vibe-coded backends pass functional tests but have no timeout, no retry budget, no circuit breaker, and no alert — and then fail silently under real load.

## Trigger

Before shipping any backend feature to production or staging. Skip for: local dev tooling, one-off migration scripts, throwaway prototypes explicitly not going to prod.

## Checklist

### Timeouts

- [ ] Every outbound HTTP call has an explicit timeout (not library default — state the value)
- [ ] DB queries have a statement timeout or are guarded by an application-level timeout
- [ ] Subprocess / shell commands have a timeout and a kill on expiry
- [ ] WebSocket connections have a ping/pong keepalive and a max-idle timeout

### Retry and Backoff

- [ ] Retryable operations have bounded retry count (not infinite)
- [ ] Retry uses exponential backoff with jitter, not fixed sleep
- [ ] Non-idempotent operations are NOT retried without dedup (e.g. payment charge, send email)
- [ ] Retry budget is tracked — after N failures, fail fast rather than hammering downstream

### Idempotency

- [ ] POST/PUT endpoints that trigger side effects are idempotent or have a client-supplied idempotency key
- [ ] Duplicate webhook/event delivery is handled (check event id before processing)
- [ ] Background jobs can be requeued safely without double-processing

### Failure Isolation

- [ ] Third-party API failure does NOT crash the primary user request (degrade gracefully or return partial result)
- [ ] DB slow / unavailable does NOT block unrelated features (connection pool limits, timeouts)
- [ ] One bad job does NOT starve the queue (per-item error handling, poison message handling)

### Observability

- [ ] Structured log entry on every significant state transition (created, started, succeeded, failed, retried)
- [ ] Log includes: request/job id, user id, operation type, duration, outcome
- [ ] Error logs include enough context to reproduce without reading source code
- [ ] Critical failure path triggers an alert (not just a log line that nobody reads)

### Anomaly Recovery

- [ ] If the process crashes mid-operation, what state is left? Is it recoverable on restart?
- [ ] Orphaned in-progress records are detectable and have a cleanup / timeout mechanism
- [ ] Health check endpoint reflects real dependency health (not just "process is alive")

## Four Questions for Each External Dependency

For each third-party service or downstream API in this feature:

1. **What happens when it's down?** (return error, queue for retry, degrade)
2. **What happens when it's slow?** (timeout value, circuit breaker threshold)
3. **What happens when it returns unexpected data?** (schema validation, fallback)
4. **What happens when it double-delivers?** (idempotency handling)

## Completion Gate

Before shipping:
- All timeouts named with explicit values.
- Retry strategy documented (max attempts, backoff, idempotency).
- One non-happy-path failure scenario walked through end-to-end.
- Monitoring / alerting confirmed active (not "we'll add it later").
