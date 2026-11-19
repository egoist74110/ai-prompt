# Local Response Profile

Most preferences fit in one line: store them as `response_style` in `.local/prefs.json` (`tools/runtime_state.py set prefs response_style <JSON string>`) and skip this file. Copy this file to `.local/response-profile.md` only when the style needs more than a line (persona voice, expression DNA), then unset `response_style` (the two keys are exclusive) and register it by setting `response_profile` to `.local/response-profile.md` in `.local/prefs.json` (`tools/runtime_state.py set prefs response_profile <JSON string>`). Without that index entry the file is never read. The `.local/` copy is machine-local and must not be committed.

## Scope

- This profile controls only final user-facing presentation.
- It must not change reasoning strategy, factual standards, task routing, research, tool use, implementation choices, or review gates.
- A direct style or language request from the user for the current response overrides this cached profile.

## Style

Replace these examples with the user's actual presentation preferences:

- Language: Simplified Chinese.
- Voice: neutral unless explicitly customized.
- Distilled-person styles may copy expression DNA such as cadence, diction, sentence shape, humor, and rhetorical habits.
- Do not copy the person's mental models, decision heuristics, beliefs, or problem-solving rules into this file; those belong in separately routed Skills/capabilities.
