---
name: resource-lifecycle-audit
description: Audit every resource opened in an implementation for a matching close/kill/unsubscribe. The most common silent killer in vibe-coded backends. Run after implementation, before claiming done.
---

# Resource Lifecycle Audit

The single most important post-implementation check for backend code. Resource leaks don't surface in tests — they compound silently in production until the process OOMs, the DB pool exhausts, or the file descriptor limit hits.

## Trigger

Run after implementing any backend feature that touches:
- subprocess, child process, shell command
- DB connection, connection pool, cursor, transaction
- Redis / cache connection
- WebSocket, TCP socket, HTTP client session
- Timer, interval, scheduled job
- File handle, temp file, stream
- Event listener, pub/sub subscription, message queue consumer
- In-memory registry, lock, semaphore, cache entry

Skip for: pure functions with no I/O, simple data transformations, static config reads.

## Audit Checklist

For each resource opened, verify:

| Resource | Opened? | Closed/Released? | On exception path? | On cancellation path? |
|---|---|---|---|---|
| DB connection | | | | |
| Subprocess | | | | |
| File handle | | | | |
| Timer/interval | | | | |
| WS / socket | | | | |
| Cache entry | | | | |
| Event listener | | | | |

Fill in actual resource names from the code being reviewed.

## Lifecycle Pairing Rules

Every open must have a paired close — enforced structurally, not by convention:

```
spawn()       → kill() / wait()
open()        → close()        (prefer context manager / with)
connect()     → disconnect()
subscribe()   → unsubscribe()
register()    → deregister()   (use try/finally or a context manager wrapper)
setTimeout()  → clearTimeout()
setInterval() → clearInterval()
```

## Red Flags

Flag any of these patterns immediately:

- `try: open()` with no `finally: close()`
- Cleanup inside `except` only (skipped on happy path or cancellation)
- Manual register/pop pairs scattered across multiple functions
- No timeout on external HTTP calls, subprocess wait, or DB query
- Temp files or cache keys with no expiry and no explicit delete
- Event listener attached inside a loop or per-request handler with no removal

## Fix Pattern

Prefer one structural owner over manual cleanup in branches:

```python
# Bad — cleanup only in one branch
conn = db.connect()
try:
    result = conn.query(...)
    conn.close()       # skipped if query raises
except:
    log_error()
    conn.close()       # duplicated

# Good — always closes
with db.connect() as conn:
    result = conn.query(...)
```

For custom resources without context manager support, wrap in `try/finally`:

```python
proc = subprocess.Popen(...)
try:
    ...
finally:
    proc.kill()
    proc.wait()
```

## Completion Gate

Before marking implementation complete:
- Every resource in the audit table has a confirmed close path.
- Each close runs on success, exception, and cancellation.
- No timeout-free external calls remain.
- State residue on crash is acceptable or documented.
