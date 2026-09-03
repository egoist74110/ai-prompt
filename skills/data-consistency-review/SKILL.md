---
name: data-consistency-review
description: Check multi-step write operations for partial failure and orphaned state — transaction boundaries, atomicity, and rollback paths. Run after implementation, before claiming done.
---

# Data Consistency Review

Catches the gap between "each step works" and "the whole operation is atomic." A single failed request that leaves the database in a half-written state is one of the hardest bugs to find — it silently accumulates until someone notices the numbers don't add up.

## Trigger

Any backend operation that involves:
- Writing to more than one table or collection in sequence
- Writing to a DB and an external service (queue, email, payment, file storage)
- Read → compute → write patterns where the read result is acted on later
- Creating a parent record and child records in separate statements

Skip for: single-row reads, pure queries, operations that touch exactly one atomic write.

## Core Question

> If this operation fails at step N, what state does the database (and every other system) end up in?

Walk through every write in the operation in order. For each one, ask: **if the next step fails, is the current state safe?**

## Three Failure Patterns to Check

### 1. Partial write — no transaction

```
write A  ← succeeds
write B  ← fails
```
A is now in the DB with no matching B. No error is surfaced to the user for A.

Fix: wrap A and B in a single DB transaction. If that is not possible (cross-service), document the failure residue and add a cleanup/reconciliation job.

### 2. Read-modify-write without locking

```
read balance  (100)
compute new   (100 - 50 = 50)
write balance (50)
```
Two concurrent requests read 100, both compute 50, both write 50 — one deduction is lost.

Fix: use `SELECT ... FOR UPDATE`, an atomic DB operation (`UPDATE balance = balance - 50 WHERE balance >= 50`), or an optimistic lock (version field + retry on conflict).

### 3. DB write + external side effect

```
charge payment API  ← succeeds
write order to DB   ← fails
```
Money is taken but no order exists. Or reversed: order exists but payment was never charged.

Fix: decide which is the source of truth. Write the DB record first in a "pending" state, then call the external API, then mark it complete. If the external call fails, the pending record is detectable and retryable. Never treat an external API call as part of a DB transaction.

## Checklist

- [ ] Every multi-step write is wrapped in a transaction, OR the partial-failure state is documented and handled
- [ ] No read-modify-write pattern without either a DB-level lock or an optimistic concurrency check
- [ ] External side effects (email, payment, queue message) happen after the DB write succeeds, not before
- [ ] If an external call fails after the DB write, the DB record reflects that (status = pending/failed), not silently left as "done"
- [ ] There is no path where a user-visible entity (order, account, job) is created without its required related records

## Completion Gate

For each multi-step write in the feature: name the failure point between each step and state what residue it leaves. If residue is acceptable, say why. If not, show the fix.
