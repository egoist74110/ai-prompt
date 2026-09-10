# Regression / Cleanup Gate

Authoritative delivery rules for implementation tasks with file/config/process/build/debug side effects.

**Complete = required behavior verified + relevant regression passed + task-owned temporary resources reclaimed + final diff/state explainable.**

## 1. Baseline and Ownership

Before the first side effect, establish only the relevant baseline.

For Git workspaces run at least:

```text
git status --short
```

Track resources as they are created:

- `baseline`: existed before the task; preserve;
- `temporary`: task-owned and not a deliverable; remove/stop/restore;
- `artifact`: requested deliverable; keep;
- `unknown`: ownership unclear; never destroy blindly.

For long-lived processes record command, PID/job, port if applicable, and purpose. Track temporary files, builds/logs/traces, config/permission changes, proxies/tunnels, browsers, workers, MCP/services, and other task-owned side effects.

Never reconstruct ownership by guesswork at cleanup time.

## 2. Regression

Verify target behavior, then the smallest meaningful adjacent scope:

1. directly relevant test/lint/typecheck/smoke;
2. shared callers/routes/build chain when affected;
3. for bug fixes, preferably both the formerly failing case and one nearby normal case.

Match validation scope to risk; do not run huge suites ceremonially. If execution is impossible, report `not run` and why. Static inspection is not a passing runtime test.

## 3. Workspace Hygiene

Before delivery, inspect at least:

```text
git status --short
git diff --check
```

Every changed/untracked file must be explained as baseline, required change, intentional artifact, or task-owned residue to remove.

Remove only confirmed task-owned temporary files/artifacts. Do not purge normal global caches.

Never use broad destructive cleanup by default, including:

```text
git clean -fd
git reset --hard
killall node
pkill python
taskkill /IM node.exe /F
```

## 4. Processes, Ports, and Configuration

Stop task-started servers/watchers/browsers/workers/MCP/tunnels/background jobs unless persistence was requested. Prefer recorded PID/job handles or the launcher's stop command.

- A disappeared PID is already stopped.
- If ownership cannot be proven, leave it untouched and report it.
- For temporary listening ports, restore the pre-task baseline; the goal is not necessarily an empty port.
- Restore task-owned temporary config/permissions such as debug flags, permissive CORS, mocks, proxies, expanded permissions, and temporary runtime arguments unless they are required deliverables.

## 5. Failure Path

Failure, abandoned approaches, failed tests, and interruptions still require safe cleanup:

```text
stop task-owned temporary resources
-> remove task-owned temporary artifacts
-> restore task-owned temporary configuration
-> preserve baseline/user state
-> report anything that cannot be handled safely
```

## 6. Post-Cleanup Smoke

After cleanup, run one minimal check that confirms the deliverable does not depend on removed temporary state, e.g. import/compile/typecheck, one critical test, CLI dry-run, configuration parse, or minimal start/clean exit.

Reclaim any new temporary resources created by this smoke.

## 7. Delivery Gate

Do not claim full completion if any known condition remains undisclosed:

- task-owned temporary files/processes remain unintentionally;
- diff/untracked changes are unexplained;
- required validation/regression was not run;
- cleanup failed;
- ownership is uncertain and therefore intentionally left untouched.

User-requested persistent services/logs/artifacts may remain; report them.

Final report should be concise: what changed, validation, cleanup/intentional retention, unmet requirements, remaining risks.
