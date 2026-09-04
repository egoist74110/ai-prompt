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

The search code resolves its CSV/data files relative to itself, so it is independent of cwd.

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
<python> <skill_dir>/scripts/search.py "<query>" --design-system --persist -p "<Project Name>" --output-dir "<project-dir>/design-system"
```

For page-specific overrides:

```text
<python> <skill_dir>/scripts/search.py "<query>" --design-system --persist -p "<Project Name>" --page dashboard --output-dir "<project-dir>/design-system"
```

Do not let the default cwd accidentally create `design-system/` inside the ai-prompt repository. Always set the target project/output directory when persisting.

### 3. Supplement only as needed

```text
<python> <skill_dir>/scripts/search.py "<keyword>" --domain style
<python> <skill_dir>/scripts/search.py "<keyword>" --domain color
<python> <skill_dir>/scripts/search.py "<keyword>" --domain typography
<python> <skill_dir>/scripts/search.py "<keyword>" --domain ux
<python> <skill_dir>/scripts/search.py "<keyword>" --domain chart
<python> <skill_dir>/scripts/search.py "<keyword>" --domain landing
```

Stack guidance:

```text
<python> <skill_dir>/scripts/search.py "layout responsive form" --stack <stack>
```

Available stack names are defined by the script; when uncertain, read `--help`/the script instead of maintaining a duplicate list here.

## Priority rules

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
