# Regression / Cleanup Gate

This file defines regression and cleanup discipline before implementation delivery. The goal is not to make AI merely **look finished**, but to leave the workspace in a state where work can safely continue.

> **A working feature does not mean the task is complete.**
>
> Complete = target implemented + required regression passed + task-created garbage removed + task-started resources reclaimed + workspace diff explainable.

Applies to code/configuration changes, tests, development servers, browser automation, temporary scripts, generated files, builds, migrations, debugging, MCP/local services, and other tasks that may create side effects.

## 0. Principles

1. **Cleanup is part of the task, not an optional optimization.** Execute it before final response.
2. **Clean only task-owned resources.** Never delete pre-existing files, terminate pre-existing processes, or free ports whose ownership cannot be established.
3. **Failure paths require cleanup too.** Reclaim temporary resources when an approach errors, is abandoned, tests fail, or another route is chosen.
4. **Intentional deliverables are not garbage.** User-requested files, required build outputs, and explicitly persistent services may remain, but must be mentioned in delivery.
5. **If safe deletion/termination cannot be proven, leave the resource alone and report it.** Never damage the user's environment merely to appear clean.

## 1. Establish a Baseline Before Side Effects

If the task may modify a workspace or start resources, establish the minimum baseline before the first side-effecting operation.

### Git Workspace

If the target is a Git repository, inspect at least:

```text
git status --short
```

When useful also inspect:

```text
git diff --stat
git diff --name-only
```

The workspace need not start clean. The purpose is to know:

- which modified/untracked files predate the task;
- which files this task creates/modifies;
- which pre-existing dirty state must survive cleanup.

### Processes / Ports

Record process/port baseline only when the task will start long-lived servers, browsers, watchers, MCP, local APIs, test workers, etc.

Record at least:

- start command;
- PID when available;
- listening port when applicable;
- working directory / service purpose.

Do not scan every process on the machine merely to establish a baseline. Inspect only names/ports relevant to the task.

## 2. Task Resource Ledger

Track resources as they are created instead of reconstructing ownership from memory at the end.

### Files

Track temporary scripts; debug patches and `.bak`/`.orig`/`.rej`; downloaded/intermediate files; temporary JSON/CSV/logs; screenshots, traces, HAR, coverage, profiling output; test artifacts; copied debugging configuration; and temporary build/output directories.

Classify them immediately:

```text
temporary -> remove during cleanup
artifact  -> requested deliverable; keep
unknown   -> reassess at cleanup; never delete blindly
```

### Processes / Services

Track dev servers, Vite/Webpack watchers, `python -m http.server`, uvicorn/gunicorn, Playwright/browser drivers, MCP servers, temporary proxies/tunnels, test workers, tail/watch/log followers, and background shell/PowerShell jobs.

Anything started temporarily for this task and not requested to persist is cleanup scope by default.

### Environment / Configuration Side Effects

Track temporary permission changes, proxies, hosts/port mappings, feature flags, credential locators, runtime configuration, and disabled security checks/services.

Process-local environment variables naturally disappear with the process and need no extra restoration. Changes written to files/system configuration must be restored unless they are part of the requested deliverable; if retained, report them.

## 3. Functional Regression

After implementation, verify the target behavior first, then check that adjacent existing behavior still works.

Choose the smallest meaningful regression scope based on the change:

1. Run directly relevant unit tests, lint, typecheck, or smoke checks first.
2. For shared functions/configuration/routes/build chains, also test adjacent callers or a higher-level smoke.
3. For bug fixes, preferably verify both:
   - the formerly failing scenario now passes;
   - one nearby normal scenario still passes.
4. If execution is impossible, state `not run` and why. Never describe static inspection as a passing runtime test.

Do not run enormous suites merely for ceremony; validation scope should match risk.

## 4. Workspace Hygiene Sweep

### A. Diff / Untracked Files

In a Git repository run at least:

```text
git status --short
git diff --check
```

Then determine:

- whether every added/modified file belongs to the requirement;
- whether temporary scripts, debug logs, patches, screenshots, or test output remain;
- whether lockfiles, repository-wide formatting, or IDE settings changed unintentionally;
- whether generated files were forgotten;
- whether `.orig`, `.rej`, `.bak`, `nohup.out`, or similar residue remains.

**Never use broad commands such as `git clean -fd` or `git reset --hard` for cleanup.** They cannot distinguish user-owned content from task-owned garbage.

### B. Temporary Files

Remove ledger entries marked `temporary` only when confirmed task-owned.

Delete tool-generated caches only when all are true:

- created by this task;
- located inside the target workspace and would pollute the repository;
- not a cache normally expected to persist in the development workflow.

Do not purge global npm/pip/browser caches merely to achieve theoretical cleanliness.

### C. Background Processes / Children

Stop task-started servers, watchers, browsers, workers, MCP services, tunnels, and background jobs unless the user requested persistence.

**Prefer recorded PID/job handles or the launcher's own stop command.**

Do not default to broad process-name termination such as:

```text
killall node
pkill python
taskkill /IM node.exe /F
```

unless the user explicitly authorizes it and the environment proves there are no unrelated matching processes.

A disappeared PID is already stopped. If a PID remains but ownership can no longer be proven, do not force-kill it; report the risk.

### D. Ports

If the task temporarily listened on a port, after stopping its process confirm that the port is no longer occupied by **that task-owned process**.

If a service already occupied the port before the task, the goal is restoration to baseline, not an empty port.

### E. Temporary Configuration / Permissions

Restore debugging-only feature flags, debug mode, permissive CORS, expanded permissions, mock endpoints, proxies, and temporary runtime arguments.

If such a change is itself part of the requirement, keep it and include it in the diff/delivery report.

## 5. Post-Cleanup Smoke

**Run one minimal smoke after cleanup.**

A feature may appear functional only because a temporary dev server, environment variable, debug file, or background process was left behind. A post-cleanup smoke confirms the deliverable state itself is sufficient.

Typical checks include:

- import / compile / typecheck;
- one critical unit test;
- CLI `--help` / dry-run;
- minimal application start followed by clean exit;
- configuration parsing.

If the smoke itself starts temporary processes or creates files, reclaim them afterward.

## 6. Failure / Interruption Path

Even when the task fails, perform every cleanup action that can be done safely:

```text
implementation failed
-> stop task-started services
-> remove task-owned temporary artifacts
-> restore temporary configuration
-> preserve pre-existing user state
-> report what remains and why it cannot be handled safely
```

Never leave a watcher, browser, or test server running merely because the implementation failed.

## 7. Delivery Decision

Do not claim full completion when any of the following is known:

- task-owned temporary files remain;
- task-owned temporary processes remain running without a user request to keep them;
- the diff contains unexplained changes;
- required regression was not run and this was not disclosed;
- cleanup failed and the failure was not disclosed.

Allowed exceptions:

- the user explicitly requested a service to keep running;
- the user requested logs/traces/artifacts to remain;
- ownership cannot be determined safely, so the resource is intentionally left untouched and reported.

Keep the final report concise:

```text
what changed
what was validated
what was cleaned / intentionally retained
remaining risks
```

Do not repeat the entire checklist to the user, but actually execute it.

## 8. One-Line Rule

> **Work as if borrowing someone else's kitchen: spread out tools while working, but before leaving, remove your garbage, temporary cookware, and anything you left running; do not throw away what was already there.**
