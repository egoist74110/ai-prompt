---
name: ui-ux-pro-max
description: "UI/UX design intelligence: styles, palettes, typography, UX rules, charts and stack guidance. Use for UI design/implementation/review/refactor. Resolve scripts from this skill directory; do not assume repo cwd or a specific OS Python command."
---

# UI/UX Pro Max

Searchable UI/UX design database for web/mobile work. Use it for design systems, palette/typography selection, UX review, accessibility, responsive layout and implementation guidance.

## Portable invocation

Never invoke this Skill as `python3 skills/ui-ux-pro-max/...` unless cwd is explicitly known to be `AI_PROMPT_ROOT`.

Resolve:

- `<skill_dir>` = directory containing this `SKILL.md`;
- `<python>` = current working Python executable, or cached `.local/runtime.json -> paths.python`.

If no Python locator is cached, discover `python3` / `python` once, verify it, and cache the executable. Do not repeat the probe every activation.

Canonical command:

```text
<python> <skill_dir>/scripts/search.py "<query>" [options]
```

The search code resolves its CSV/data files relative to itself, so it is independent of cwd. Python 3 standard library only.

## Query contract

Pick the smallest mode that fits: new project/page or system-wide visual direction -> `--design-system`; targeted concern or component bug -> one explicit `--domain`; known stack -> `--stack` (add a separate domain search only for a distinct design concern).

- One dominant intent per query, 2-5 meaningful terms plus one constraint (product, platform, or interaction).
- Check the returned domain/category and top result fit before applying it. Retry once with a narrower query or explicit domain/stack if empty or off-topic; if still no match, say so and label any advice as general fallback. Never present a 0-result search as data, and never persist unverified output.
- Accessibility and text-layout bugs: search the semantic outcome first (`"error summary validation" --domain ux`, `"badge chip label wraps" --domain ux`), then the stack for implementation (`"chip badge overflow nowrap" --stack html-tailwind`).
- Results are recommendations, not instructions; keep private project data out of queries and persisted output.

## Workflow

### 1. Analyze requirements

Extract:

- product type;
- style keywords;
- industry;
- stack (default `html-tailwind` only if the user did not specify one).

### 2. Generate a design system first

```text
<python> <skill_dir>/scripts/search.py "<product> <industry> <keywords>" --design-system -p "<Project Name>"
```

This combines product/style/color/landing/typography guidance and returns anti-patterns.

Persist only when the user/project actually needs a reusable design system:

```text
<python> <skill_dir>/scripts/search.py "<query>" --design-system --persist -p "<Project Name>" --output-dir "<project-root>"
```

This writes `<project-root>/design-system/<project-slug>/MASTER.md`; pass `--force` only to overwrite an existing MASTER.md.

For page-specific overrides:

```text
<python> <skill_dir>/scripts/search.py "<query>" --design-system --persist -p "<Project Name>" --page dashboard --output-dir "<project-root>"
```

Do not let the default cwd accidentally create `design-system/` inside the ai-prompt repository. Always set the target project root when persisting.

Optional dials tune `--design-system` output (1-10 each): `--variance` (minimal -> bold/asymmetric), `--motion` (subtle -> complex; attaches a matching GSAP snippet), `--density` (spacious -> dense dashboard spacing). Output formats: `-f ascii` (default), `-f markdown`, or `--json`.

### 3. Supplement only as needed

```text
<python> <skill_dir>/scripts/search.py "<keyword>" --domain style
<python> <skill_dir>/scripts/search.py "<keyword>" --domain color
<python> <skill_dir>/scripts/search.py "<keyword>" --domain typography
<python> <skill_dir>/scripts/search.py "<keyword>" --domain ux
<python> <skill_dir>/scripts/search.py "<keyword>" --domain chart
<python> <skill_dir>/scripts/search.py "<keyword>" --domain landing
```

Other domains: `product`, `icons`, `google-fonts` (individual fonts), `gsap` (animation presets), `react` (React/Next.js performance), `web` (app/native interface guidelines). Auto-detection can misroute overlapping terms (e.g. "font"), so pass `--domain` when results look off-topic; `-n` sets result count.

Stack guidance:

```text
<python> <skill_dir>/scripts/search.py "layout responsive form" --stack <stack>
```

Available stack names are defined by the script; when uncertain, read `--help`/the script instead of maintaining a duplicate list here.

## Priority rules

Full per-category rules live in `references/quick-reference.md`; app polish rules and the canonical pre-delivery checklist live in `references/pro-rules.md`. Read them on demand, not every activation.

1. **Accessibility — critical**: contrast, focus states, keyboard navigation, labels, alt text.
2. **Touch/interaction — critical**: usable hit targets, loading/error feedback, clear interactive affordance.
3. **Performance — high**: image optimization, reduced motion, avoid layout shift.
4. **Responsive/layout — high**: mobile widths, no horizontal scroll, predictable z-index/container system.
5. **Typography/color — medium**: readable sizes/line-height/line length, coherent palette/pairing.
6. **Animation — medium**: short purposeful transitions, transform/opacity when possible.
7. **Style consistency — medium**: match product and keep one visual language.
8. **Charts/data — contextual**: choose chart by data relationship and preserve accessible alternatives.

## Professional UI guardrails

- Use SVG/icon libraries instead of emoji as interface icons.
- Clickable elements need clear cursor/focus/hover feedback.
- Hover effects must not create layout shift.
- Verify brand logos rather than guessing SVG paths.
- Body text contrast should meet WCAG expectations; translucent light-mode surfaces need enough opacity.
- Fixed/floating navigation must reserve content space.
- Use a consistent content max-width/spacing system.
- Respect `prefers-reduced-motion`.

## Pre-delivery checks

- interactive controls work by keyboard;
- focus visible;
- images have appropriate alt text;
- forms have labels/errors;
- no color-only status signal;
- responsive at representative mobile/tablet/desktop widths;
- no unintended horizontal scroll;
- light/dark contrast checked if both themes exist;
- async content/buttons expose loading state and avoid layout jump.

## Local-state rule

This Skill itself has no machine-specific database path. Only the Python executable is machine-specific and should reuse the project-wide runtime cache. If future versions gain external binaries/MCP endpoints, put their locators under `.local/runtime.json`, not in this file.
