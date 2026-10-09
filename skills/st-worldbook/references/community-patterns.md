# Community patterns for making and maintaining World Info

This reference summarizes reusable approaches from SillyTavern's official documentation, a community World Info encyclopedia, and existing community creation tools/prompts. They are patterns to adapt, not mandatory schemas. The local user conventions in [authoring.md](authoring.md) and the requested book take precedence.

## A practical hybrid workflow

### Start from a brief or existing material

Community builders support two useful entry points: a single premise with guided choices, or an existing book/lore source loaded for editing. For new, larger books, turn the brief into an inventory and a compact setting overview before drafting details. Keep the user's chosen facts and unresolved questions visible; lock or mark confirmed material so subsequent expansion does not casually rewrite it. For small tasks, go straight to the requested entries.

The [LoreBook Creator](https://github.com/virgilianshailer/lorebook-creator) demonstrates premise-led and guided creation, adjustable scale, per-field/per-entry editing, loading an existing World Info JSON, and building new books from selected lore. Its staged audit separates deterministic mechanical checks from judgment-based LLM suggestions. This is a useful workbench model even when the work is done in conversation rather than in that extension.

### Organize by useful entry types, not a fixed taxonomy

Possible buckets include core rules/concepts, people, factions, locations, objects, events/history, creatures, culture, and RP controls. Choose only the categories the setting needs. A category inventory helps spot missing or uneven coverage, while the final book can remain a simple keyed set of entries.

For recurring expansions or character variants, consider a small shared/core book plus focused supplemental books. Keep this optional: one book is simpler unless separation supports reuse or prevents unrelated context from being loaded. The community [Canonize lorebook design](https://github.com/ZapoVerde/SillyTavern-Canonize/blob/main/docs/lorebook.md) illustrates category lanes and separate files; its sync ownership rules and fixed tags are specific to that project, not general SillyTavern requirements.

### Design activation around how people actually chat

- Use names, common aliases, and distinctive phrases that are likely to appear naturally. A key's presence activates the entry; the key and title themselves are not included in the inserted content, so write a complete content body.
- Avoid broad keys that match ordinary conversation or trigger many unrelated entries. Where a generic concept needs narrowing, consider secondary-key logic, character filters, or a more specific alias; do not add these mechanics by default.
- Keep the initial design mostly direct-key activated. Use recursive links only when an activated entry mentioning another entity should predictably bring that entity's details into context. Guard static or potentially expansive entries against unwanted recursion.
- Placement and order affect the prompt's final use and budget priority. Choose them for the entry's function and keep priority differences meaningful; a high order does not itself mean “more important” in every sense.

These ideas align with the [official World Info documentation](https://docs.sillytavern.app/usage/core-concepts/worldinfo/) and the community [World Info Encyclopedia](https://rentry.co/world-info-encyclopedia). The encyclopedia includes opinions and examples tied to particular character formats and older UI behavior; do not copy its suggested settings as universal defaults.

### Audit in two passes

**Mechanical pass** — inspect format and activation wiring: valid standalone `entries` object, unique entry IDs, valid keys, non-constant entries with no trigger, secondary keys without selective mode, empty or duplicate keys, and settings that do not have an effect (for example, `depth` when the entry is not at depth). Preserve fields the user did not ask to change.

**Behavior pass** — inspect likely collisions and outcomes: ordinary words activating too much, the same entry duplicating another, constant entries consuming budget, long entries that activate too easily, inconsistent canon, and recursive chains that pull in a large portion of the book. Automated or deterministic checks can flag candidates; semantic overlap and whether prose is useful require judgment.

The creator tool documents examples of deterministic checks (`no_keys`, ineffective secondary keys, duplicate/colliding/generic keys, constant bloat, and ineffective depth) and distinguishes them from subjective optimization. Treat any numeric thresholds in tools as heuristics for that tool, not SillyTavern limits.

### Iterate with actual prompts

The official docs describe World Info as dynamically inserted context and recommend concise content. In practice, validate a few representative prompts: one that should trigger an entry, a nearby prompt that should not, and a case that tests any intended recursion or secondary-key condition. If SillyTavern is available and the user wants live validation, inspect the prompt/debug output rather than assuming a valid JSON file proves good activation. Otherwise, make the activation cases explicit in the handoff so they can be tested in chat.

## Sources

- SillyTavern Docs, [World Info](https://docs.sillytavern.app/usage/core-concepts/worldinfo/)
- kingbri, Alicat, Trappu, [World Info Encyclopedia](https://rentry.co/world-info-encyclopedia)
- virgilianshailer, [LoreBook Creator](https://github.com/virgilianshailer/lorebook-creator)
- ZapoVerde, [SillyTavern-Canonize lorebook architecture](https://github.com/ZapoVerde/SillyTavern-Canonize/blob/main/docs/lorebook.md)
- r/SillyTavernAI community prompt, [Universe builder/lorebook creation example](https://www.reddit.com/r/SillyTavernAI/comments/1sk34xd/this_prompt_i_made_with_claude_to_generate_worlds/)
