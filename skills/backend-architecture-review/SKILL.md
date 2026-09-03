---
name: backend-architecture-review
description: Use before implementing any backend feature — ask the five architecture questions first, then approve the data model and access boundary before writing code.
---

# Backend Architecture Review

Run this before writing backend code for a new feature, endpoint, or data flow. The goal is a 5-minute verbal safety check, not a formal document.

## Trigger

Any new backend feature, API endpoint, background job, or data integration. Skip for: trivial config changes, one-liner patches, pure frontend work.

## Five Questions to Answer First

Answer all five in plain text before touching code:

1. **What data does this produce?**
   List every field written to DB, cache, queue, or external service. If uncertain, name the candidate tables/stores.

2. **Where does data come from and where does it go?**
   Trace the full path: caller → this service → downstream. Name each hop.

3. **Who can access this data?**
   Which roles/users are allowed to read and write. What happens if an unauthenticated or low-privilege request arrives.

4. **Can concurrent requests conflict?**
   Two users hitting the endpoint simultaneously — do they race on the same row, queue message, or cache key? If yes, what's the isolation strategy (DB transaction, lock, queue dedup).

5. **What's the failure mode and cleanup?**
   If this operation fails halfway through, what state is left behind? Is it safe to retry? Will anything be orphaned?

## Architecture Choices to State Upfront

- **DB schema**: new table / new column / existing table. Migration risk?
- **Caching**: what is cached, TTL, invalidation trigger.
- **Queue/async**: is this sync or async? If async, who reads the result and when?
- **Permission model**: row-level, role-level, or resource ownership check — state which.

## Implementation Gate

Do not write implementation code until all five answers exist and the data model is agreed. If any answer is "unsure", resolve it (ask the user, check the schema) before proceeding.
