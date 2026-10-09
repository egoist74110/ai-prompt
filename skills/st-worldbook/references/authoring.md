# Worldbook authoring

These are the user's preferred writing conventions. Adapt them to the requested book and existing style rather than treating every count or format as a validity rule.

## Practical creation workflow

1. Decide the deliverable: a few entry drafts, a standalone World Info JSON, or a change to a live local book. Use the matching output format; standalone World Info entries use the keyed `entries` object described in the operations reference, not the Character Card V2 embedded `character_book` shape.
2. Gather the source material that actually defines the canon. For a new or substantial setting, build a compact inventory of core rules, people, places, groups, objects, events, and unresolved questions. Confirm material gaps or conflicting facts before expanding the inventory. For a small, clear request, skip the ceremony and draft directly.
3. Sketch the book at the requested scale. Start with only the categories relevant to the roleplay; separate always-needed rules from conditional details. Do not force every common category or invent a target entry count.
4. Draft entries as standalone context: each content body should make sense without its title or trigger keywords. Add distinctive natural aliases as keys; use secondary keys only where a real AND/NOT condition improves precision.
5. Audit the whole book: entries that cannot trigger, ineffective secondary keys, generic or colliding triggers, duplicated coverage, contradictions, excessive always-on content, and unnecessary recursive chains. Fix deterministic mechanical defects directly; use judgment and preserve alternatives for subjective edits.
6. Review a representative activation path: what user/chat text activates each important entry, what else activates with it, and whether recursion adds useful context or noise. When the user can test in SillyTavern, suggest trying a few real prompts and adjusting keys before growing the book further.

When editing an existing book, present or apply changes as targeted edits, preserve unrelated entries and schema fields, and compare before/after where practical. For large books, work in batches or by category and checkpoint accepted entries so later edits do not overwrite them.

For community examples behind these patterns and their limits, see [community-patterns.md](community-patterns.md).

## Structure and activation

- For a setting book, use a short always-on overview for core rules when needed. Put people, places, factions, items, and events in keyword-triggered detail entries so irrelevant text stays out of the prompt.
- Choose 1–3 distinctive entity-name triggers, often two or fewer. Avoid broad common words that activate unrelated entries. Relationship entries can use both parties' names.
- Use short noun-phrase `comment` titles, usually 2–6 Chinese characters for Chinese entries. Keep meaningful names in other languages intact. Avoid redundant hierarchy prefixes.
- Mind the token budget: each `constant` entry is considered every turn; higher `order` entries get budget priority. Do not inflate `order` merely to control visual placement.

## Content

- Prefer concise key-value facts and lists. One sentence should carry one idea. Use exact numbers, measurements, times, and names when the source supports them; do not invent precision.
- Describe setting rules, mechanisms, tendencies, and possibilities. For events, record time, cause, outcome, and impact as reference information rather than a scene.
- Keep characters and future events open where appropriate: express common behavior and plausible exceptions rather than fixing every future action.
- Edit each sentence by asking: Does it change understanding? Is it information or decoration? Would a list be clearer? Can it stand alone without the source text?
- Detail entries often need a few hundred dense characters, but let the amount of useful information set the length.

## Special cases

- Character entry: give identity, traits with observable behavior, capabilities, and relationships. Split long entries when retrieval or budget benefits; if several entries share a trigger, set `order` for the desired budget priority. A compact PList-style form can help: `[name: 身份, 底色:特质(行为), has(能力), 关系: 与XX是YY]`.
- Relationship entry: specify relation type and a concrete interaction or historical event; avoid bare labels such as “关系很好”.
- Output-format or control entry: put instructions in a dedicated entry, choose an appropriate `position`, and delimit examples clearly. The fact-entry preference above does not prohibit instructions in entries whose purpose is control.
- Mod pack: define its scope and activation controls in a lean overview when needed. Keep optional subsystems disabled by default when the user should choose them, use specific triggers for each subsystem, and avoid activating mutually exclusive variants together. Decide the actual semantics of a new loader or switch panel with the user before writing it.
